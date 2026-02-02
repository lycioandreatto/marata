# --- PÁGINA: DESEMPENHO DE VENDAS (FATURADO)
elif menu_interna == "📊 Desempenho de Vendas":
    st.header("📊 Desempenho de Vendas (Faturado)")

    try:
        # 1. Leitura das abas
        df_faturado = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
        df_metas_cob = conn.read(spreadsheet=url_planilha, worksheet="META COBXPOSIT")
        df_param_metas = conn.read(spreadsheet=url_planilha, worksheet="PARAM_METAS")
        df_meta_sistema = conn.read(spreadsheet=url_planilha, worksheet="META SISTEMA")
        df_2025 = conn.read(spreadsheet=url_planilha, worksheet="META 2025")

        lista_hierarquia_fixa = [
            "ACHOCOLATADO","ACUCAR","ADOCANTE SACARINA","ADOCANTE SUCRALOSE","AZEITONA",
            "BALSAMICO","BEBIDA MISTA","CALDOS TABLETE","CATCHUP","CEBOLINHA","COGUMELO",
            "DESCARTAVEIS","ESPECIARIAS","FARINHA DE TRIGO FD","FARINHA DE TRIGO SC",
            "FARINHA LACTEA","MACARRAO INSTANTANEO","MARATINHO","MILHO",
            "MILHO FARINHA GOTA","MILHO FARINHA MARATA","MILHO FLOCAO GOTA",
            "MILHO FLOCAO MARATA","MILHO PIPOCA","MINGAU","MISTURA BOLO",
            "MOLHO PRONTO","MOLHOS ALHO","MOLHOS INGLES","MOLHOS LIMAO",
            "MOLHOS PIMENTA","MOLHOS PIMENTA 75ML","MOLHOS SALSA","MOLHOS SHOYO",
            "MOLHOS TEMPEROS CASEIROS","OLEAGINOSAS","PIMENTA CONSERVA",
            "PIPOCA PRONTA","REFRESCO","SALGADINHOS FARDO","SALGADINHOS NACHOS",
            "SALGADINHOS PASTEIS","SUCO D+ 1000ML","SUCO D+ 200ML",
            "SUCO MARATA 1000ML","SUCO MARATA 200ML","TEMPERO COLORIFICO GOTA",
            "TEMPERO COLORIFICO MARATA","TEMPERO CONDIMENTO GOTA",
            "TEMPERO CONDIMENTO MARATA","TEMPERO EM PO","VINAGRE","VINAGRE ESPECIAL"
        ]

        if df_faturado is not None and not df_faturado.empty:
            df_faturado = df_faturado.dropna(how="all")
            df_faturado.columns = [str(c).strip() for c in df_faturado.columns]

            df_faturado.rename(columns={
                "Região de vendas": "VENDEDOR_NOME",
                "RG": "VENDEDOR_COD",
                "Qtd Vendas (S/Dec)": "QTD_VENDAS",
                "Hierarquia de produtos": "HIERARQUIA"
            }, inplace=True)

            col_cod_cliente = df_faturado.columns[10]

            df_faturado["QTD_VENDAS"] = pd.to_numeric(df_faturado["QTD_VENDAS"], errors="coerce").fillna(0)
            df_faturado["VENDEDOR_COD"] = df_faturado["VENDEDOR_COD"].astype(str).str.replace(r"\.0$", "", regex=True)

            df_relacao = df_base[["VENDEDOR","SUPERVISOR","ANALISTA"]].drop_duplicates("VENDEDOR")
            df_faturado = df_faturado.merge(
                df_relacao, left_on="VENDEDOR_NOME", right_on="VENDEDOR", how="left"
            )

        # ✅ (NECESSÁRIO) Garantir base_total e META CLIENTES/PENDÊNCIA (usadas na tabela/cards)
        if df_param_metas is not None:
            df_param_metas.columns = [str(c).strip() for c in df_param_metas.columns]
            if "BASE" in df_param_metas.columns:
                df_param_metas["BASE"] = pd.to_numeric(df_param_metas["BASE"], errors="coerce").fillna(0)
            if "EscrV" in df_param_metas.columns:
                df_param_metas["EscrV"] = df_param_metas["EscrV"].astype(str).str.strip()

        if df_metas_cob is not None:
            df_metas_cob.columns = [str(c).strip() for c in df_metas_cob.columns]
            if "RG" in df_metas_cob.columns:
                df_metas_cob["RG"] = df_metas_cob["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "BASE" in df_metas_cob.columns:
                df_metas_cob["BASE"] = pd.to_numeric(df_metas_cob["BASE"], errors="coerce").fillna(0)
            if "META COBERTURA" in df_metas_cob.columns:
                df_metas_cob["META COBERTURA"] = (
                    pd.to_numeric(df_metas_cob["META COBERTURA"], errors="coerce")
                    .fillna(0)
                    .apply(lambda x: x / 100 if x > 1 else x)
                )
            if "META" in df_metas_cob.columns:
                df_metas_cob["META"] = pd.to_numeric(df_metas_cob["META"], errors="coerce").fillna(0)

        if df_meta_sistema is not None:
            df_meta_sistema.columns = [str(c).strip() for c in df_meta_sistema.columns]
            if "RG" in df_meta_sistema.columns:
                df_meta_sistema["RG"] = df_meta_sistema["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "QTD" in df_meta_sistema.columns:
                df_meta_sistema["QTD"] = pd.to_numeric(df_meta_sistema["QTD"], errors="coerce").fillna(0)

        if df_2025 is not None:
            df_2025.columns = [str(c).strip() for c in df_2025.columns]
            if "RG" in df_2025.columns:
                df_2025["RG"] = df_2025["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "QUANTIDADE" in df_2025.columns:
                df_2025["QUANTIDADE"] = pd.to_numeric(df_2025["QUANTIDADE"], errors="coerce").fillna(0)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        st.stop()

    # ============================
    # BASE PRINCIPAL
    # ============================
    df_f = df_faturado.copy()

    # ============================
    # 🔒 CONTROLE DE ACESSO
    # ============================
    df_base_perm = df_base.copy()

    for c in ["VENDEDOR","SUPERVISOR","ANALISTA"]:
        if c in df_base_perm.columns:
            df_base_perm[c] = df_base_perm[c].astype(str).str.strip().str.upper()

    user_atual = user_atual.strip().upper()
    vendedores_permitidos = None

   # ✅ (CONDIÇÕES) Admin/Diretoria veem tudo; Analista vê seus supervisores/vendedores; Supervisor vê seus vendedores; Vendedor vê só ele
if is_analista:
    vendedores_permitidos = (
        df_base_perm.loc[df_base_perm["ANALISTA"] == user_atual, "VENDEDOR"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

elif is_supervisor:
    vendedores_permitidos = (
        df_base_perm.loc[df_base_perm["SUPERVISOR"] == user_atual, "VENDEDOR"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

elif is_vendedor:
    vendedores_permitidos = [user_atual]

# 🔒 APLICA O FILTRO CORRETO POR PERFIL
if vendedores_permitidos:
    # Normaliza colunas pra não falhar comparação
    if "VENDEDOR" in df_f.columns:
        df_f["VENDEDOR"] = df_f["VENDEDOR"].astype(str).str.strip().str.upper()
    if "VENDEDOR_NOME" in df_f.columns:
        df_f["VENDEDOR_NOME"] = df_f["VENDEDOR_NOME"].astype(str).str.strip().str.upper()

    # Analista e Supervisor filtram pelo VENDEDOR (coluna do df_base após merge)
    if is_analista or is_supervisor:
        if "VENDEDOR" in df_f.columns:
            df_f = df_f[df_f["VENDEDOR"].isin(vendedores_permitidos)]
        else:
            # fallback de segurança (caso não exista a coluna VENDEDOR)
            df_f = df_f[df_f["VENDEDOR_NOME"].isin(vendedores_permitidos)]

    # Vendedor vê SOMENTE ele mesmo (pelo nome do faturado)
    elif is_vendedor:
        df_f = df_f[df_f["VENDEDOR_NOME"] == user_atual]

# ============================
# 🔍 FILTROS
# ============================
st.markdown("### 🔍 Filtros")
c1, c2, c3 = st.columns(3)

with c1:
    # ✅ Estado vem do df_base ("Estado"); como no seu código estava "EscrV", aqui mantemos sem quebrar:
    # se existir "EscrV" usa; senão usa "Estado"
    col_estado = "EscrV" if "EscrV" in df_f.columns else ("Estado" if "Estado" in df_f.columns else None)
    sel_estado = st.multiselect("Estado", sorted(df_f[col_estado].dropna().unique())) if col_estado else []
if sel_estado and col_estado:
    df_f = df_f[df_f[col_estado].isin(sel_estado)]

with c2:
    sel_supervisor = st.multiselect("Supervisor", sorted(df_f["SUPERVISOR"].dropna().unique()))
if sel_supervisor:
    df_f = df_f[df_f["SUPERVISOR"].isin(sel_supervisor)]

with c3:
    sel_vendedor = st.multiselect("Vendedor", sorted(df_f["VENDEDOR_NOME"].dropna().unique()))
if sel_vendedor:
    df_f = df_f[df_f["VENDEDOR_NOME"].isin(sel_vendedor)]

vendedores_ids = df_f["VENDEDOR_COD"].unique()


    # ============================
    # BASE TOTAL (NECESSÁRIA PARA CARDS/TABELA)
    # ============================
    base_total = 0
    if df_param_metas is not None and not df_param_metas.empty and col_estado:
        if not (sel_supervisor or sel_vendedor):
            dados_base = df_param_metas[df_param_metas["EscrV"].isin(df_f[col_estado].unique())] if "EscrV" in df_param_metas.columns else df_param_metas.copy()
            if "BASE" in dados_base.columns:
                base_total = float(dados_base["BASE"].sum())
        else:
            if df_metas_cob is not None and "RG" in df_metas_cob.columns:
                dados_base = df_metas_cob[df_metas_cob["RG"].isin(vendedores_ids)]
                if "BASE" in dados_base.columns:
                    base_total = float(dados_base.drop_duplicates("RG")["BASE"].sum())

    # ============================
    # PROCESSAMENTO FINAL
    # ============================
    df_agrup_f = (
        df_f.groupby("HIERARQUIA")
        .agg({"QTD_VENDAS":"sum", col_cod_cliente:"nunique"})
        .rename(columns={"QTD_VENDAS":"VOLUME", col_cod_cliente:"POSITIVAÇÃO"})
        .reset_index()
    )

    # Metas 2025/2026 por RG (se existirem)
    df_agrup_25 = (
        df_2025[df_2025["RG"].isin(vendedores_ids)]
        .groupby("HIERARQUIA DE PRODUTOS")["QUANTIDADE"]
        .sum()
        .reset_index()
        .rename(columns={"HIERARQUIA DE PRODUTOS":"HIERARQUIA","QUANTIDADE":"META 2025"})
        if df_2025 is not None and not df_2025.empty and "HIERARQUIA DE PRODUTOS" in df_2025.columns
        else pd.DataFrame(columns=["HIERARQUIA","META 2025"])
    )

    df_agrup_26 = (
        df_meta_sistema[df_meta_sistema["RG"].isin(vendedores_ids)]
        .groupby("HIERARQUIA DE PRODUTOS")["QTD"]
        .sum()
        .reset_index()
        .rename(columns={"HIERARQUIA DE PRODUTOS":"HIERARQUIA","QTD":"META 2026"})
        if df_meta_sistema is not None and not df_meta_sistema.empty and "HIERARQUIA DE PRODUTOS" in df_meta_sistema.columns
        else pd.DataFrame(columns=["HIERARQUIA","META 2026"])
    )

    df_meta_cob_h = (
        df_metas_cob.groupby("HIERARQUIA DE PRODUTOS")["META COBERTURA"]
        .mean()
        .reset_index()
        .rename(columns={"HIERARQUIA DE PRODUTOS":"HIERARQUIA"})
        if df_metas_cob is not None and not df_metas_cob.empty and "HIERARQUIA DE PRODUTOS" in df_metas_cob.columns
        else pd.DataFrame(columns=["HIERARQUIA","META COBERTURA"])
    )

    df_final = pd.DataFrame(lista_hierarquia_fixa, columns=["HIERARQUIA"])
    df_final = df_final.merge(df_agrup_f, on="HIERARQUIA", how="left")
    df_final = df_final.merge(df_meta_cob_h, on="HIERARQUIA", how="left")
    df_final = df_final.merge(df_agrup_25, on="HIERARQUIA", how="left")
    df_final = df_final.merge(df_agrup_26, on="HIERARQUIA", how="left").fillna(0)

    # ✅ colunas que seu layout usa
    df_final["META CLIENTES (ABS)"] = (df_final["META COBERTURA"] * base_total).apply(math.ceil) if base_total > 0 else 0
    df_final["PENDÊNCIA CLIENTES"] = (df_final["META CLIENTES (ABS)"] - df_final["POSITIVAÇÃO"]).apply(lambda x: x if x > 0 else 0)
    df_final["CRESCIMENTO 2025"] = df_final["VOLUME"] - df_final.get("META 2025", 0)
    df_final["ATINGIMENTO % (VOL 2025)"] = (df_final["VOLUME"] / df_final.get("META 2025", 0) * 100).replace([np.inf, -np.inf], 0).fillna(0)
    df_final["CRESCIMENTO 2026"] = df_final["VOLUME"] - df_final.get("META 2026", 0)
    df_final["ATINGIMENTO % (VOL 2026)"] = (df_final["VOLUME"] / df_final.get("META 2026", 0) * 100).replace([np.inf, -np.inf], 0).fillna(0)

    df_final.rename(columns={"HIERARQUIA":"HIERARQUIA DE PRODUTOS"}, inplace=True)

    # --- UI: CARDS E TABELA ---
    st.markdown("---")
    col_res, col_cob, col_pos = st.columns([1.2, 1, 1])

    # ✅ CARD 1 (MANTIDO): COBERTURA ATUAL (NÃO MEXIDO)
    with col_cob:
        real_perc = (df_f[col_cod_cliente].nunique() / base_total * 100) if base_total > 0 else 0
        st.markdown(
            f"""
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                <small>COBERTURA ATUAL</small><br>
                <span style="font-size: 1.1em;">Base: <b>{base_total:,.0f}</b></span><br>
                Atingido: <span style="color:#28a745; font-size: 1.8em; font-weight: bold;">{real_perc:.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ✅ CARD 2 (NOVO): POSITIVAÇÃO (META COBXPOSIT -> colunas RG, BASE, META)
    with col_pos:
        if not (sel_supervisor or sel_vendedor) and ("EqVs" in df_f.columns):
            positivos_total = df_f.loc[~df_f["EqVs"].isin(["STR", "SMX"]), col_cod_cliente].nunique()
        else:
            positivos_total = df_f[col_cod_cliente].nunique()

        dados_pos = df_metas_cob[df_metas_cob["RG"].isin(vendedores_ids)].drop_duplicates("RG") if df_metas_cob is not None else pd.DataFrame()

        base_pos = pd.to_numeric(dados_pos["BASE"], errors="coerce").fillna(0).sum() if "BASE" in dados_pos.columns else 0

        meta_pos = pd.to_numeric(dados_pos["META"], errors="coerce").fillna(0).mean() if "META" in dados_pos.columns else 0
        meta_pos = (meta_pos / 100) if meta_pos > 1 else meta_pos

        meta_abs = math.ceil(base_pos * meta_pos) if base_pos > 0 else 0
        perc_pos = (positivos_total / meta_abs * 100) if meta_abs > 0 else 0

        st.markdown(
            f"""
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                <small>POSITIVAÇÃO</small><br>
                <span style="font-size: 1.1em;">Meta: <b>{meta_pos:.0%}</b></span><br>
                <span style="font-size: 1.1em;">Positivados: <b>{positivos_total:,.0f}</b></span><br>
                Atingido: <span style="color:#1f77b4; font-size: 1.8em; font-weight: bold;">{perc_pos:.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📈 Desempenho por Hierarquia")

    df_view = df_final.copy()
    df_view[" "] = ""
    df_view["  "] = ""
    df_view["   "] = ""
    df_view["    "] = ""

    cols_view = [
        "HIERARQUIA DE PRODUTOS",
        "META COBERTURA",
        "META CLIENTES (ABS)",
        "POSITIVAÇÃO",
        "PENDÊNCIA CLIENTES",
        " ",
        "META 2025",
        "META 2026",
        "  ",
        "VOLUME",
        "   ",
        "CRESCIMENTO 2025",
        "ATINGIMENTO % (VOL 2025)",
        "    ",
        "CRESCIMENTO 2026",
        "ATINGIMENTO % (VOL 2026)",
    ]

    def zebra_rows(row):
        return ["background-color: #FAFAFA" if row.name % 2 else "" for _ in row]

    def destacar_negativos(s):
        return ["background-color: #FFE5E5; color: #7A0000; font-weight: 600" if v < 0 else "" for v in s]

    def destacar_pendencia(s):
        return ["background-color: #FFD6D6; color: #7A0000; font-weight: 700" if v > 0 else "" for v in s]

    def limpar_espacos(s):
        return ["background-color: transparent" for _ in s]

    sty = (
        df_view[cols_view]
        .sort_values(by="HIERARQUIA DE PRODUTOS")
        .style
        .format(
            {
                "META COBERTURA": "{:.0%}",
                "META CLIENTES (ABS)": "{:,.0f}",
                "POSITIVAÇÃO": "{:,.0f}",
                "PENDÊNCIA CLIENTES": "{:,.0f}",
                "META 2025": "{:,.0f}",
                "META 2026": "{:,.0f}",
                "VOLUME": "{:,.0f}",
                "CRESCIMENTO 2025": "{:,.0f}",
                "ATINGIMENTO % (VOL 2025)": "{:.1f}%",
                "CRESCIMENTO 2026": "{:,.0f}",
                "ATINGIMENTO % (VOL 2026)": "{:.1f}%",
            }
        )
        .apply(zebra_rows, axis=1)
        .apply(destacar_pendencia, subset=["PENDÊNCIA CLIENTES"])
        .apply(destacar_negativos, subset=["CRESCIMENTO 2025", "CRESCIMENTO 2026"])
        .apply(limpar_espacos, subset=[" ", "  ", "   ", "    "])
        .set_table_styles(
            [
                {"selector": "th", "props": [("background-color", "#F2F2F2"), ("color", "#111"), ("font-weight", "700")]},
                {"selector": "td", "props": [("border-bottom", "1px solid #EEE")]},
            ]
        )
    )

    st.dataframe(
        sty,
        use_container_width=True,
        hide_index=True,
        height=560,
    )

    # Exportação
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Dashboard")
    st.download_button("📥 Baixar Excel", buffer.getvalue(), "relatorio.xlsx", "application/vnd.ms-excel")
    st.markdown("---")

    if st.button("📧 Enviar Excel por Vendedor"):

        import smtplib
        email_origem = st.secrets["email"]["sender_email"]
        senha_origem = st.secrets["email"]["sender_password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_origem, senha_origem)

        vendedores = df_f['VENDEDOR_NOME'].unique()

        for vendedor in vendedores:
            vendedor_up = vendedor.upper()

            email_destino = MAPA_EMAIL_VENDEDORES.get(
                vendedor_up,
                "lycio.oliveira@marata.com.br"
            )

            df_vendedor = df_final.copy()

            enviar_excel_vendedor(
                server=server,
                email_origem=email_origem,
                email_destino=email_destino,
                nome_vendedor=vendedor,
                df_excel=df_vendedor
            )

        server.quit()
        st.success("📨 E-mails enviados com sucesso!")
