# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda Completa")
    
    if df_agenda is not None and not df_agenda.empty:
        # 1. Preparação para Previsibilidade
        df_agenda['DT_COMPLETA'] = pd.to_datetime(df_agenda['DATA'], dayfirst=True, errors='coerce')
        # Nome dos dias em português para facilitar a análise
        dias_traducao = {
            'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
            'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df_agenda['DIA_SEMANA'] = df_agenda['DT_COMPLETA'].dt.day_name().map(dias_traducao)

        # Filtro de visibilidade por perfil
        if is_admin or is_diretoria:
            df_user = df_agenda.copy()
        elif is_analista:
            df_user = df_agenda[df_agenda['ANALISTA'].str.upper() == user_atual].copy()
        else:
            df_user = df_agenda[df_agenda['SUPERVISOR'] == user_atual].copy()

        if not df_user.empty:
            # Trazer Cidade (Garantindo que a coluna exista antes da exportação)
            if df_base is not None and 'CIDADE' not in df_user.columns:
                col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
                df_cidades = df_base[['Cliente', col_local_base]].copy()
                df_user = pd.merge(df_user, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left')
                df_user.rename(columns={col_local_base: 'CIDADE'}, inplace=True)

            # --- CÁLCULO DOS CONTADORES ---
            def extrair_dist(val):
                try:
                    s = str(val).replace('m', '').replace('Erro GPS', '0')
                    return float(s) if (s != 'nan' and s.strip() != "") else 0
                except: return 0
            
            # Garantir que DISTANCIA_LOG existe para não dar erro no apply
            if 'DISTANCIA_LOG' not in df_user.columns:
                df_user['DISTANCIA_LOG'] = ""
            
            df_user['dist_val_calc'] = df_user['DISTANCIA_LOG'].apply(extrair_dist)

            # --- EXIBIÇÃO DOS CARDS ---
            total_agendado = len(df_user)
            total_pendente = len(df_user[df_user['STATUS'] == "Planejado"])
            total_realizado = len(df_user[df_user['STATUS'] == "Realizado"])
            
            if is_admin or is_diretoria or is_analista:
                cols = st.columns(4)
                fora_raio = len(df_user[(df_user['STATUS'] == "Realizado") & (df_user['dist_val_calc'] > 50)])
                cols[3].metric("📍 Fora do Raio (>50m)", fora_raio, 
                              delta=f"{fora_raio} Alertas" if fora_raio > 0 else None, 
                              delta_color="inverse")
            else:
                cols = st.columns(3)

            cols[0].metric("📅 Total Agendado", total_agendado)
            cols[1].metric("⏳ Total Pendente", total_pendente)
            cols[2].metric("✅ Total Realizado", total_realizado)
            
            st.markdown("---")

            # --- BLOCO DE EXPORTAÇÃO (COM VALIDAÇÃO DE COLUNAS) ---
            import io
            from fpdf import FPDF
            
            cols_desejadas = ['DATA', 'REGISTRO', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'CIDADE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']
            if (is_admin or is_diretoria or is_analista):
                cols_desejadas.append('DISTANCIA_LOG')
            
            # FILTRO DE SEGURANÇA: Só exporta o que realmente existe no dataframe
            cols_v = [c for c in cols_desejadas if c in df_user.columns]
            
            df_export = df_user[cols_v].copy()
            exp_col1, exp_col2, exp_col3 = st.columns([1, 1, 8])
            
            with exp_col1:
                buffer_ex = io.BytesIO()
                with pd.ExcelWriter(buffer_ex, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, index=False, sheet_name='Agenda')
                st.download_button(label="📥 Excel", data=buffer_ex.getvalue(), file_name=f"Agenda_{user_atual}.xlsx", mime="application/vnd.ms-excel")

            with exp_col2:
                try:
                    pdf = FPDF(orientation='L', unit='mm', format='A4')
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, f"Relatorio - {user_atual}", ln=True, align='C')
                    pdf.set_font("Arial", size=7) # Fonte menor para caber mais colunas
                    col_width = (pdf.w - 20) / len(cols_v)
                    for col in cols_v: pdf.cell(col_width, 10, str(col), border=1)
                    pdf.ln()
                    for _, row in df_export.iterrows():
                        for item in row: pdf.cell(col_width, 10, str(item)[:15], border=1)
                        pdf.ln()
                    pdf_output = pdf.output(dest='S').encode('latin-1', errors='replace')
                    st.download_button(label="📥 PDF", data=pdf_output, file_name=f"Agenda_{user_atual}.pdf", mime="application/pdf")
                except: st.error("Erro ao gerar PDF")

            # --- LÓGICA DA TABELA ---
            df_user["AÇÃO"] = False
            
            def style_agenda_completa(row):
                if is_admin or is_diretoria or is_analista:
                    if row['STATUS'] == "Realizado":
                        return ['color: #E67E22; font-weight: bold'] * len(row) if row['dist_val_calc'] > 50 else ['color: green; font-weight: bold'] * len(row)
                return [''] * len(row)

            cols_display = ['AÇÃO'] + cols_v + ['dist_val_calc']
            # Filtro de segurança para exibição também
            cols_display = [c for c in cols_display if c in df_user.columns or c == 'AÇÃO']
            
            df_display = df_user[cols_display].copy()
            df_styled = df_display.style.apply(style_agenda_completa, axis=1)

            config_col = {
                "AÇÃO": st.column_config.CheckboxColumn("📌"),
                "REGISTRO": st.column_config.TextColumn("🕒 Registro"),
                "dist_val_calc": None
            }
            if not (is_admin or is_diretoria or is_analista):
                if "DISTANCIA_LOG" in df_display.columns: config_col["DISTANCIA_LOG"] = None
            else:
                config_col["DISTANCIA_LOG"] = st.column_config.TextColumn("📍 Dist. GPS")

            edicao_user = st.data_editor(
                df_styled, key="edit_full_agenda_actions", hide_index=True, 
                use_container_width=True, column_config=config_col,
                disabled=[c for c in cols_display if c != "AÇÃO"]
            )

            # --- GERENCIAMENTO (SOMENTE REAGENDAR) ---
            marcados = edicao_user[edicao_user["AÇÃO"] == True]
            if not marcados.empty:
                idx = marcados.index[0]
                sel_row = df_user.iloc[idx]
                
                st.markdown(f"### ⚙️ Gerenciar: {sel_row['CLIENTE']}")
                st.info("O histórico original será preservado para análise de previsibilidade.")
                
                n_data = st.date_input("Nova Data de Visita:", value=datetime.now())
                if st.button("Confirmar Reagendamento"):
                    import pytz
                    fuso = pytz.timezone('America/Sao_Paulo')
                    agora_br = datetime.now(fuso).strftime('%d/%m/%Y %H:%M:%S')
                    
                    nova_v = sel_row.copy()
                    nova_v['ID'] = str(uuid.uuid4())
                    nova_v['DATA'] = n_data.strftime('%d/%m/%Y')
                    nova_v['REGISTRO'] = agora_br
                    nova_v['STATUS'] = "Planejado"
                    nova_v['JUSTIFICATIVA'] = ""; nova_v['DISTANCIA_LOG'] = ""; nova_v['COORDENADAS'] = ""
                    nova_v['AGENDADO POR'] = user_atual
                    
                    # Remover colunas temporárias antes de salvar na planilha
                    cols_to_drop = ['AÇÃO', 'dist_val_calc', 'CIDADE', 'LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'Cliente_y', 'Cliente_x']
                    nova_v_dict = nova_v.drop(labels=cols_to_drop, errors='ignore').to_frame().T
                    
                    df_final = pd.concat([df_agenda, nova_v_dict], ignore_index=True)
                    # Limpeza final antes de subir
                    df_final = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns], errors='ignore')
                    
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear()
                    st.success("Reagendado!")
                    time.sleep(1); st.rerun()
        else:
            st.info("Nenhum agendamento encontrado.")
    else:
        st.warning("Agenda vazia.")
