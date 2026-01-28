# --- PÁGINA: DASHBOARD ---
elif menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento por Supervisor")
    
    if df_base is not None and df_agenda is not None:
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'Analista')
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')

        # --- NOVO INSIGHT: RANKING SAUDÁVEL (GAMIFICAÇÃO) ---
        st.markdown("### 🏆 Ranking de Performance (Adesão)")
        
        # Cálculo do Ranking Geral para Gamificação
        resumo_geral_base = df_base.groupby(col_rv_base).size().reset_index(name='Total')
        resumo_geral_agenda = df_agenda.groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Agendados')
        df_ranking = pd.merge(resumo_geral_base, resumo_geral_agenda, left_on=col_rv_base, right_on='SUPERVISOR', how='left').fillna(0)
        df_ranking['%'] = (df_ranking['Agendados'] / df_ranking['Total'] * 100).round(1)
        df_ranking = df_ranking.sort_values(by='%', ascending=False).reset_index(drop=True)
        
        # Visualização de Medalhas para o Top 3
        if not df_ranking.empty:
            m1, m2, m3 = st.columns(3)
            with m1:
                if len(df_ranking) >= 1:
                    st.markdown(f"<div style='text-align:center; padding:10px; border:2px solid #FFD700; border-radius:10px;'>🥇 1º {df_ranking.iloc[0][col_rv_base]}<br><span style='font-size:20px;'>{df_ranking.iloc[0]['%']}%</span></div>", unsafe_allow_html=True)
            with m2:
                if len(df_ranking) >= 2:
                    st.markdown(f"<div style='text-align:center; padding:10px; border:2px solid #C0C0C0; border-radius:10px;'>🥈 2º {df_ranking.iloc[1][col_rv_base]}<br><span style='font-size:20px;'>{df_ranking.iloc[1]['%']}%</span></div>", unsafe_allow_html=True)
            with m3:
                if len(df_ranking) >= 3:
                    st.markdown(f"<div style='text-align:center; padding:10px; border:2px solid #CD7F32; border-radius:10px;'>🥉 3º {df_ranking.iloc[2][col_rv_base]}<br><span style='font-size:20px;'>{df_ranking.iloc[2]['%']}%</span></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        # --- FIM DO RANKING ---

        st.subheader("Filtros de Visualização")
        f_c1, f_c2 = st.columns(2)
        
        df_base_filtrada = df_base.copy()
        
        with f_c1:
            if is_admin or is_diretoria:
                lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
                ana_sel_dash = st.selectbox("Escolher Analista:", ["Todos"] + lista_analistas, key="ana_dash")
                if ana_sel_dash != "Todos":
                    df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base] == ana_sel_dash]
            else: 
                ana_sel_dash = user_atual
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base].str.upper() == user_atual]

        with f_c2:
            lista_sups_dash = sorted([str(s) for s in df_base_filtrada[col_rv_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
            sup_sel_dash = st.selectbox("Escolher Supervisor:", ["Todos"] + lista_sups_dash, key="sup_dash")
            if sup_sel_dash != "Todos":
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_rv_base] == sup_sel_dash]

        df_reg_agenda = df_agenda[['CÓDIGO CLIENTE', 'REGISTRO']].copy().drop_duplicates(subset='CÓDIGO CLIENTE', keep='last')
        df_base_detalhe = df_base_filtrada.copy()
        df_base_detalhe = pd.merge(df_base_detalhe, df_reg_agenda, left_on='Cliente', right_on='CÓDIGO CLIENTE', how='left')
        
        df_base_detalhe['STATUS AGENDAMENTO'] = df_base_detalhe['REGISTRO'].apply(
            lambda x: 'AGENDADO' if pd.notnull(x) and str(x).strip() != "" and str(x) != "-" else 'PENDENTE'
        )
        df_base_detalhe['REGISTRO'] = df_base_detalhe['REGISTRO'].fillna("-")
        
        df_relatorio_completo = df_base_detalhe[['REGISTRO', col_rv_base, 'Cliente', 'Nome 1', col_local_base, 'STATUS AGENDAMENTO']]
        df_relatorio_completo.columns = ['REGISTRO', 'SUPERVISOR', 'CÓDIGO', 'CLIENTE', 'CIDADE', 'STATUS']
        df_relatorio_completo = df_relatorio_completo.sort_values(by='STATUS')

        resumo_base = df_base_filtrada.groupby(col_rv_base).size().reset_index(name='Total na Base')
        resumo_agenda = df_agenda[df_agenda['CÓDIGO CLIENTE'].isin(df_base_filtrada['Cliente'])].groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Já Agendados')
        
        df_dash = pd.merge(resumo_base, resumo_agenda, left_on=col_rv_base, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Já Agendados'] = df_dash['Já Agendados'].astype(int)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Já Agendados']
        df_dash['% Conclusão'] = (df_dash['Já Agendados'] / df_dash['Total na Base'] * 100).round(1).astype(str) + '%'
        df_dash = df_dash[[col_rv_base, 'Total na Base', 'Já Agendados', 'Faltando', '% Conclusão']]
        df_dash.columns = ['SUPERVISOR', 'CLIENTES NA BASE', 'CLIENTES AGENDADOS', 'FALTANDO', '% DE ADESÃO']
        
        exp_c1, exp_c2, _ = st.columns([1, 1, 2])
        with exp_c1:
            st.download_button("📥 Relatório Detalhado (Excel)", data=converter_para_excel(df_relatorio_completo), file_name="detalhamento_agendamentos.xlsx")
        with exp_c2:
            try:
                st.download_button("📄 Relatório Detalhado (PDF)", data=gerar_pdf(df_relatorio_completo, tipo_relatorio="DASH"), file_name="detalhamento_agendamentos.pdf")
            except:
                st.error("Erro ao gerar PDF do detalhamento")
        
        st.dataframe(df_dash, use_container_width=True, hide_index=True)
        
        c1, c2, c3, c4 = st.columns(4)
        total_base = df_dash['CLIENTES NA BASE'].sum()
        total_agendados = df_dash['CLIENTES AGENDADOS'].sum()
        total_pendente = df_dash['FALTANDO'].sum()
        percent_adesao = (total_agendados / total_base * 100) if total_base > 0 else 0
        
        c1.metric("Total Clientes Base (Filtro)", total_base)
        c2.metric("Total Agendados (Filtro)", total_agendados)
        c3.metric("Pendente Total (Filtro)", total_pendente)
        c4.metric("% Adesão Total", f"{percent_adesao:.1f}%")
        
    else:
        st.error("Dados insuficientes para gerar o Dashboard.")
