# --- PÁGINA: VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    if df_agenda is not None and not df_agenda.empty:
        f_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + sorted(df_agenda['SUPERVISOR'].unique()))
        df_f = df_agenda.copy()
        if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]

        # Exportação (Código original mantido)
        df_exportar = df_f[['REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']]
        c_exp1, c_exp2, _ = st.columns([1, 1, 2])
        with c_exp1:
            st.download_button("📥 Excel", data=converter_para_excel(df_exportar), file_name="agenda_marata.xlsx", use_container_width=True)
        with c_exp2:
            try: st.download_button("📄 PDF", data=gerar_pdf(df_exportar), file_name="agenda_marata.pdf", use_container_width=True)
            except: st.error("Erro no PDF")

        # Tabela de Edição
        df_f["EDITAR"] = False 
        cols_v = ['EDITAR', 'REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        edicao = st.data_editor(
            df_f[cols_v],
            column_config={"EDITAR": st.column_config.CheckboxColumn("📝", default=False)},
            disabled=[c for c in cols_v if c != "EDITAR"],
            hide_index=True,
            use_container_width=True,
            key="editor_final_v8"
        )

        linhas_marcadas = edicao[edicao["EDITAR"] == True]
        if not linhas_marcadas.empty:
            idx = linhas_marcadas.index[0]
            dados = df_f.loc[idx]
            id_s = dados['ID']
            st.markdown(f"---")
            st.subheader(f"⚙️ Opções para: {dados['CLIENTE']}")
            
            # --- AJUSTE AQUI: Justificativa fora do formulário para habilitar a caixa dinâmica ---
            st_list = ["Planejado (X)", "Realizado", "Reagendado"]
            ju_list = list(df_just.iloc[:, 0].dropna().unique())
            if "OUTRO" not in ju_list: ju_list.append("OUTRO")
            
            col_escolha1, col_escolha2 = st.columns(2)
            with col_escolha1:
                n_st = st.radio("Status:", st_list, index=st_list.index(dados['STATUS']) if dados['STATUS'] in st_list else 0)
            with col_escolha2:
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(dados['JUSTIFICATIVA']) if dados['JUSTIFICATIVA'] in ju_list else 0)
                
                # A caixa de texto aparece IMEDIATAMENTE aqui
                motivo_outro = ""
                if n_ju == "OUTRO":
                    motivo_outro = st.text_input("Digite o motivo específico:", placeholder="Escreva aqui...")

            # O Formulário agora contém apenas os botões de ação para salvar os dados capturados acima
            with st.form("form_botoes_acao"):
                b_at, b_ex = st.columns(2)
                with b_at:
                    if st.form_submit_button("✅ SALVAR ALTERAÇÕES", use_container_width=True):
                        just_final = motivo_outro if n_ju == "OUTRO" and motivo_outro.strip() != "" else n_ju
                        
                        df_agenda.loc[df_agenda['ID'] == id_s, ['STATUS', 'JUSTIFICATIVA']] = [n_st, just_final]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                        st.cache_data.clear()
                        st.success("Atualizado!")
                        st.rerun()
                with b_ex:
                    if st.form_submit_button("🗑️ EXCLUIR AGENDAMENTO", use_container_width=True):
                        df_novo = df_agenda[df_agenda['ID'] != id_s].drop(columns=['LINHA'], errors='ignore')
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_novo)
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("Agenda vazia.")
