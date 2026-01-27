import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

# --- FUNÇÃO COM CACHE PARA NÃO ESTOURAR A COTA DO GOOGLE ---
@st.cache_data(ttl=600) # Guarda os dados por 10 minutos
def carregar_dados_cache():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE").dropna(how='all')
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS").dropna(how='all')
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA").dropna(how='all')
        
        # Limpeza de colunas
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_j.columns = [str(c).strip() for c in df_j.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
        
        if 'ID' in df_a.columns:
            df_a['ID'] = df_a['ID'].astype(str)
            
        return df_b, df_j, df_a
    except Exception as e:
        return None, None, None

# Carregamento
df_base, df_just, df_agenda = carregar_dados_cache()

if df_base is None:
    st.error("Limite de acessos do Google atingido. Aguarde 1 minuto e recarregue a página.")
    st.stop()

# --- INTERFACE ---
menu = st.sidebar.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

if menu == "Novo Agendamento":
    st.header("📋 Novo Agendamento de Visita")
    col_sup = 'Região de vendas'
    
    supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            opcoes_just = df_just.iloc[:, 0].dropna().unique()
            with st.form("form_novo"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa_sel = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                if st.form_submit_button("💾 SALVAR NA AGENDA"):
                    cod_c, nom_c = cliente_escolhido.split(" - ", 1)
                    novo_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    
                    nova_linha = pd.DataFrame([{"ID": novo_id, "DATA": data_visita.strftime("%d/%m/%Y"), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": justificativa_sel, "STATUS": status}])
                    
                    # Para salvar, pegamos a agenda mais recente sem cache
                    df_agenda_recente = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
                    df_final = pd.concat([df_agenda_recente, nova_linha], ignore_index=True)
                    
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear() # Limpa o cache para mostrar o dado novo
                    st.success("✅ Agendado!")
                    st.rerun()

elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    
    if not df_agenda.empty:
        supervisores_agenda = sorted(df_agenda['SUPERVISOR'].unique())
        filtro_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + supervisores_agenda)
        
        df_filtrado = df_agenda.copy()
        if filtro_sup != "Todos":
            df_filtrado = df_filtrado[df_filtrado['SUPERVISOR'] == filtro_sup]

        cols_visiveis = [c for c in df_filtrado.columns if c != 'ID']
        st.dataframe(df_filtrado[cols_visiveis], use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Atualizar Status")
        
        dict_escolha = {f"{row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_filtrado.iterrows()}
        escolha_label = st.selectbox("Selecione a visita:", ["Selecione..."] + list(dict_escolha.keys()))

        if escolha_label != "Selecione...":
            id_sel = dict_escolha[escolha_label]
            match = df_agenda[df_agenda['ID'] == id_sel]
            
            if not match.empty:
                dados_visita = match.iloc[0]
                with st.form("form_edicao"):
                    status_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    idx_status = status_list.index(dados_visita['STATUS']) if dados_visita['STATUS'] in status_list else 0
                    just_list = list(df_just.iloc[:, 0].dropna().unique())
                    idx_just = just_list.index(dados_visita['JUSTIFICATIVA']) if dados_visita['JUSTIFICATIVA'] in just_list else 0

                    novo_status = st.radio("Novo Status:", status_list, index=idx_status)
                    nova_just = st.selectbox("Nova Justificativa:", just_list, index=idx_just)

                    if st.form_submit_button("✅ ATUALIZAR"):
                        df_agenda_recente = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
                        df_agenda_recente.loc[df_agenda_recente['ID'].astype(str) == id_sel, 'STATUS'] = novo_status
                        df_agenda_recente.loc[df_agenda_recente['ID'].astype(str) == id_sel, 'JUSTIFICATIVA'] = nova_just
                        
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda_recente)
                        st.cache_data.clear() # Limpa o cache para a tabela atualizar
                        st.success("✅ Atualizado!")
                        st.rerun()
