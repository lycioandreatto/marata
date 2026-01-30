# --- PÁGINA: DESEMPENHO DE VENDAS (FATURADO) ---
elif menu_interna == "📊 Desempenho de Vendas":
    st.header("📊 Desempenho de Vendas (Faturado)")
    
    try:
        # 1. Leitura das abas
        df_faturado = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
        df_metas_cob = conn.read(spreadsheet=url_planilha, worksheet="META COBXPOSIT")
        df_param_metas = conn.read(spreadsheet=url_planilha, worksheet="PARAM_METAS")
        
        lista_hierarquia_fixa = [
            "ACHOCOLATADO", "ACUCAR", "ADOCANTE SACARINA", "ADOCANTE SUCRALOSE", "AZEITONA", 
            "BALSAMICO", "BEBIDA MISTA", "CALDOS TABLETE", "CATCHUP", "CEBOLINHA", "COGUMELO", 
            "DESCARTAVEIS", "ESPECIARIAS", "FARINHA DE TRIGO FD", "FARINHA DE TRIGO SC", 
            "FARINHA LACTEA", "MACARRAO INSTANTANEO", "MARATINHO", "MILHO", "MILHO FARINHA GOTA", 
            "MILHO FARINHA MARATA", "MILHO FLOCAO GOTA", "MILHO FLOCAO MARATA", "MILHO PIPOCA", 
            "MINGAU", "MISTURA BOLO", "MOLHO PRONTO", "MOLHOS ALHO", "MOLHOS INGLES", 
            "MOLHOS LIMAO", "MOLHOS PIMENTA", "MOLHOS PIMENTA 75ML", "MOLHOS SALSA", 
            "MOLHOS SHOYO", "MOLHOS TEMPEROS CASEIROS", "OLEAGINOSAS", "PIMENTA CONSERVA", 
            "PIPOCA PRONTA", "REFRESCO", "SALGADINHOS FARDO", "SALGADINHOS NACHOS", 
            "SALGADINHOS PASTEIS", "SUCO D+ 1000ML", "SUCO D+ 200ML", "SUCO MARATA 1000ML", 
            "SUCO MARATA 200ML", "TEMPERO COLORIFICO GOTA", "TEMPERO COLORIFICO MARATA", 
            "TEMPERO CONDIMENTO GOTA", "TEMPERO CONDIMENTO MARATA", "TEMPERO EM PO", 
            "VINAGRE", "VINAGRE ESPECIAL"
        ]

        if df_faturado is not None and not df_faturado.empty:
            df_faturado = df_faturado.dropna(how='all')
            df_faturado.columns = [str(c).strip() for c in df_faturado.columns]
            
            df_faturado.rename(columns={
                'Região de vendas': 'VENDEDOR_NOME',
                'RG': 'VENDEDOR_COD', 
                'Qtd Vendas (S/Dec)': 'QTD_VENDAS',
                'Hierarquia de produtos': 'HIERARQUIA'
            }, inplace=True)

            df_faturado['QTD_VENDAS'] = pd.to_numeric(df_faturado['QTD_VENDAS'], errors='coerce').fillna(0)
            df_faturado['VENDEDOR_COD'] = df_faturado['VENDEDOR_COD'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            def aplicar_agrupamento_custom(item):
                item = str(item).strip().upper()
                mapeamento = {
                    'DESCARTAVEIS COPOS': 'DESCARTAVEIS', 'DESCARTAVEIS PRATOS': 'DESCARTAVEIS', 
                    'DESCARTAVEIS TAMPAS': 'DESCARTAVEIS', 'DESCARTAVEIS POTES': 'DESCARTAVEIS',
                    'MILHO CANJICA': 'MILHO', 'MILHO CANJIQUINHA': 'MILHO', 
                    'MILHO CREME MILHO': 'MILHO', 'MILHO FUBA': 'MILHO',
                    'MOLHOS ALHO PICANTE': 'MOLHOS ALHO',
                    'PIMENTA CONSERVA BIQUINHO': 'PIMENTA CONSERVA', 
                    'PIMENTA CONSERVA PASTA': 'PIMENTA CONSERVA'
                }
                return mapeamento.get(item, item)
            
            df_faturado['HIERARQUIA'] = df_faturado['HIERARQUIA'].apply(aplicar_agrupamento_custom)
            df_relacao = df_base[['VENDEDOR', 'SUPERVISOR', 'ANALISTA']].drop_duplicates(subset=['VENDEDOR'])
            df_faturado = pd.merge(df_faturado, df_relacao, left_on='VENDEDOR_NOME', right_on='VENDEDOR', how='left')
            df_faturado['ANALISTA'] = df_faturado['ANALISTA'].fillna('NÃO CADASTRADO')
            df_faturado['SUPERVISOR'] = df_faturado['SUPERVISOR'].fillna('NÃO CADASTRADO')
            col_k = 'K' if 'K' in df_faturado.columns else df_faturado.columns[10]

        if df_param_metas is not None:
            df_param_metas.columns = [str(c).strip() for c in df_param_metas.columns]
            df_param_metas['BASE'] = pd.to_numeric(df_param_metas['BASE'], errors='coerce').fillna(0)
            metas_raw = pd.to_numeric(df_param_metas['META_COB'].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce').fillna(0)
            df_param_metas['META_COB'] = metas_raw.apply(lambda x: x * 100 if x > 0 and x <= 1.0 else x)
            df_param_metas['EscrV'] = df_param_metas['EscrV'].astype(str).str.strip()

        if df_metas_cob is not None:
            df_metas_cob.columns = [str(c).strip() for c in df_metas_cob.columns]
            df_metas_cob['RG'] = df_metas_cob['RG'].astype(str).str.strip()
            df_metas_cob['BASE'] = pd.to_numeric(df_metas_cob['BASE'], errors='coerce').fillna(0)
            metas_vend_raw = pd.to_numeric(df_metas_cob['META'].astype(str).str.replace('%','').str.replace(',','.'), errors='coerce').fillna(0)
            df_metas_cob['META'] = metas_vend_raw.apply(lambda x: x * 100 if x > 0 and x <= 1.0 else x)

    except Exception as e:
        st.error(f"Erro no processamento das abas: {e}")
        st.stop()

    if df_faturado is not None and not df_faturado.empty:
        df_f = df_faturado.copy()
        
        st.markdown("### 🔍 Filtros")
        c0, c2, c3 = st.columns(3)
        
        with c0:
            sel_estado = st.multiselect("Estado", sorted(df_f['EscrV'].dropna().unique()))
        
        with c2:
            df_temp_sup = df_f[df_f['EscrV'].isin(sel_estado)] if sel_estado else df_f
            sel_supervisor = st.multiselect("Supervisor", sorted(df_temp_sup['SUPERVISOR'].dropna().unique()))
            
        with c3:
            df_temp_vend = df_temp_sup[df_temp_sup['SUPERVISOR'].isin(sel_supervisor)] if sel_supervisor else df_temp_sup
            sel_vendedor = st.multiselect("Vendedor", sorted(df_temp_vend['VENDEDOR_NOME'].dropna().unique()))

        if sel_estado: df_f = df_f[df_f['EscrV'].isin(sel_estado)]
        if sel_supervisor: df_f = df_f[df_f['SUPERVISOR'].isin(sel_supervisor)]
        if sel_vendedor: df_f = df_f[df_f['VENDEDOR_NOME'].isin(sel_vendedor)]

        if not df_f.empty:
            if not (sel_supervisor or sel_vendedor):
                df_limpo = df_f[~df_f['EqVs'].astype(str).str.contains('SMX|STR', na=False)] if 'EqVs' in df_f.columns else df_f
                positivacao = df_limpo[col_k].nunique()
                dados_meta = df_param_metas[df_param_metas['EscrV'].isin(df_f['EscrV'].unique())]
                base_total = dados_meta['BASE'].sum() if not dados_meta.empty else 1
                meta_val = dados_meta['META_COB'].mean() if not dados_meta.empty else 0
            else:
                positivacao = df_f[col_k].nunique()
                vendedores_ids = [str(x) for x in df_f['VENDEDOR_COD'].unique()]
                dados_meta = df_metas_cob[df_metas_cob['RG'].isin(vendedores_ids)]
                base_total = dados_meta['BASE'].sum() if not dados_meta.empty else 1
                meta_val = dados_meta['META'].mean() if not dados_meta.empty else 0
            
            real_perc = (positivacao / base_total * 100) if base_total > 0 else 0
            cor_indicador = "#28a745" if real_perc >= meta_val else "#e67e22"

            st.markdown("---")
            m1, m2, m3 = st.columns([1, 1, 2])
            
            vol_formatado = f"{df_f['QTD_VENDAS'].sum():,.0f}".replace(",", ".")
            pos_formatado = f"{positivacao:,.0f}".replace(",", ".")
            
            m1.metric("📦 Volume Total", vol_formatado)
            m2.metric("🏪 Positivados", pos_formatado)
            
            with m3:
                estados_str = ", ".join(map(str, df_f['EscrV'].unique()))
                base_formatada = f"{base_total:,.0f}".replace(",", ".")
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                    <small style="color: #666;">COBERTURA ({estados_str})</small><br>
                    <span style="font-size: 1.1em;">Base: <b>{base_formatada}</b> | Meta: <b>{meta_val:.0f}%</b></span><br>
                    Atingido: <span style="color:{cor_indicador}; font-size: 1.4em; font-weight: bold;">{real_perc:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("### 📈 Desempenho por Hierarquia")
        df_f_agrupado = df_f.groupby('HIERARQUIA').agg({'QTD_VENDAS': 'sum', col_k: 'nunique'}).rename(columns={'QTD_VENDAS': 'Volume', col_k: 'Positivação'}).reset_index()
        df_final_h = pd.merge(pd.DataFrame(lista_hierarquia_fixa, columns=['HIERARQUIA']), df_f_agrupado, on='HIERARQUIA', how='left').fillna(0)
        
        st.dataframe(
            df_final_h.sort_values(by=['HIERARQUIA'], ascending=True).style.format({
                'Volume': lambda x: f"{x:,.0f}".replace(",", "."), 
                'Positivação': lambda x: f"{x:,.0f}".replace(",", ".")
            }), 
            use_container_width=True, 
            hide_index=True
        )
