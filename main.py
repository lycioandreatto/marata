# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("🔍 Minha Agenda Completa")
    
    with col_btn:
        if st.button("🔄 Atualizar Dados", key="btn_refresh_agenda"):
            st.cache_data.clear()
            st.rerun()
    
    if df_agenda is not None and not df_agenda.empty:
        # --- 1. LIMPEZA DE DUPLICADOS E RESET DE ÍNDICE ---
        df_agenda = df_agenda.drop_duplicates(
            subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'], 
            keep='first'
        ).reset_index(drop=True)
        
        # Garantir que colunas essenciais existam
        colunas_necessarias = ['APROVACAO', 'OBS_GESTAO', 'ANALISTA', 'SUPERVISOR', 'VENDEDOR', 'DISTANCIA_LOG']
        for col in colunas_necessarias:
            if col not in df_agenda.columns:
                df_agenda[col] = 0 if col == 'DISTANCIA_LOG' else ""

        # Padronização de valores vazios
        df_agenda['APROVACAO'] = df_agenda['APROVACAO'].fillna("Pendente").replace(["", "none", "None", "nan", "NaN"], "Pendente")

        # --- 2. PREPARAÇÃO DE DATAS ---
        df_agenda['DT_COMPLETA'] = pd.to_datetime(df_agenda['DATA'], dayfirst=True, errors='coerce')

        # --- 3. LÓGICA DE FILTRO POR HIERARQUIA ---
        if is_admin or is_diretoria:
            df_user = df_agenda.copy()
            st.info("💡 Visão de Administrador: Todos os registros exibidos.")
        elif is_analista:
            df_user = df_agenda[df_agenda['ANALISTA'].astype(str).str.upper() == user_atual.upper()].copy()
        elif is_supervisor:
            df_user = df_agenda[df_agenda['SUPERVISOR'].astype(str).str.upper() == user_atual.upper()].copy()
        else:
            df_user = df_agenda[df_agenda['VENDEDOR'].astype(str).str.upper() == user_atual.upper()].copy()

        df_user = df_user.reset_index(drop=True)

        if not df_user.empty:
            # --- 4. FILTROS DINÂMICOS ---
            with st.expander("🎯 Filtros de Visualização", expanded=False):
                f_col1, f_col2, f_col3 = st.columns(3)
                def get_options(df, col):
                    return ["Todos"] + sorted([str(x) for x in df[col].unique() if x and str(x).lower() != 'nan'])

                ana_f = f_col1.selectbox("Filtrar Analista:", get_options(df_user, 'ANALISTA'))
                df_temp = df_user if ana_f == "Todos" else df_user[df_user['ANALISTA'] == ana_f]
                
                sup_f = f_col2.selectbox("Filtrar Supervisor:", get_options(df_temp, 'SUPERVISOR'))
                df_temp = df_temp if sup_f == "Todos" else df_temp[df_temp['SUPERVISOR'] == sup_f]
                
                vend_f = f_col3.selectbox("Filtrar Vendedor:", get_options(df_temp, 'VENDEDOR'))
                
                if ana_f != "Todos": df_user = df_user[df_user['ANALISTA'] == ana_f]
                if sup_f != "Todos": df_user = df_user[df_user['SUPERVISOR'] == sup_f]
                if vend_f != "Todos": df_user = df_user[df_user['VENDEDOR'] == vend_f]
                df_user = df_user.reset_index(drop=True)

            # --- 5. CARD DE ALERTA DE DISTÂNCIA (NOVO) ---
            # Identifica atendimentos realizados fora do raio (> 50m)
            df_user['DISTANCIA_LOG'] = pd.to_numeric(df_user['DISTANCIA_LOG'], errors='coerce').fillna(0)
            fora_raio = df_user[(df_user['STATUS'] == "Realizado") & (df_user['DISTANCIA_LOG'] > 50)]
            
            if not fora_raio.empty:
                st.warning(f"⚠️ **Atenção:** Foram encontrados **{len(fora_raio)}** atendimentos realizados fora do raio de 50m.")

            # --- 6. MÉTRICAS ---
            m1, m2, m3 = st.columns(3)
            m1.metric("📅 Total Agendado", len(df_user))
            m2.metric("⏳ Total Pendente", len(df_user[df_user['STATUS'] == "Planejado"]))
            m3.metric("✅ Total Realizado", len(df_user[df_user['STATUS'] == "Realizado"]))
            st.markdown("---")

            # --- 7. TABELA COM ESTILIZAÇÃO POR CORES (NOVO) ---
            df_user["AÇÃO"] = False
            
            # Função para aplicar cores nas linhas
            def style_por_distancia(row):
                if row['STATUS'] == "Realizado":
                    if row['DISTANCIA_LOG'] > 50:
                        return ['background-color: #FFF9C4'] * len(row) # Amarelo (Fora do Raio)
                    else:
                        return ['background-color: #C8E6C9'] * len(row) # Verde (Dentro do Raio)
                return [''] * len(row)

            cols_display = ['AÇÃO', 'DATA', 'ANALISTA', 'VENDEDOR', 'CLIENTE', 'STATUS', 'APROVACAO', 'DISTANCIA_LOG', 'OBS_GESTAO']
            df_display = df_user[[c for c in cols_display if c in df_user.columns or c == "AÇÃO"]].copy()

            edicao_user = st.data_editor(
                df_display.style.apply(style_por_distancia, axis=1), 
                key="edit_agenda_final_v4", 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "AÇÃO": st.column_config.CheckboxColumn("📌"),
                    "DISTANCIA_LOG": st.column_config.NumberColumn("Distância (m)", format="%d m"),
                    "DATA": st.column_config.TextColumn("Data"),
                    "ANALISTA": st.column_config.TextColumn("Analista")
                },
                disabled=[c for c in df_display.columns if c != "AÇÃO"]
            )
            
            # --- 8. GERENCIAMENTO INDIVIDUAL ---
            marcados = edicao_user[edicao_user["AÇÃO"] == True]
            if not marcados.empty:
                idx_selecionado = marcados.index[0]
                sel_row = df_user.iloc[idx_selecionado]
                
                st.markdown(f"### ⚙️ Gerenciar: {sel_row['CLIENTE']}")
                t1, t2, t3 = st.tabs(["⚖️ Aprovação", "🔄 Reagendar", "🗑️ Excluir"])
                
                with t1:
                    if is_admin or is_diretoria or is_analista:
                        col_ind1, col_ind2 = st.columns(2)
                        n_status = col_ind1.selectbox("Decisão:", ["Aprovado", "Reprovado"], key="n_status_ind")
                        n_obs = col_ind2.text_input("Motivo:", value=str(sel_row['OBS_GESTAO']), key="n_obs_ind")
                        
                        if st.button("Salvar Decisão Individual"):
                            df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['APROVACAO', 'OBS_GESTAO']] = [n_status, n_obs]
                            if n_status == "Reprovado":
                                df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Reprovado"
                            
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                            st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()
                    else:
                        st.warning("Apenas gestores podem alterar a aprovação.")

                with t2:
                    n_data = st.date_input("Nova Data:", value=datetime.now(), key="date_reag")
                    if st.button("Confirmar Reagendamento"):
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['DATA', 'STATUS', 'APROVACAO']] = [n_data.strftime('%d/%m/%Y'), "Planejado", "Pendente"]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                        st.cache_data.clear(); st.success("Reagendado!"); time.sleep(1); st.rerun()
                
                with t3:
                    st.error("Atenção: Esta ação excluirá o registro permanentemente.")
                    if st.button("🗑️ CONFIRMAR EXCLUSÃO"):
                        df_agenda = df_agenda[df_agenda['ID'] != sel_row['ID']]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                        st.cache_data.clear(); st.success("Excluído"); time.sleep(1); st.rerun()
        else:
            st.info("Nenhum agendamento encontrado para os filtros selecionados.")
