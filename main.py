import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

# --- FUNÇÃO DE CARREGAMENTO COM PROTEÇÃO (CACHE) ---
@st.cache_data(ttl=600) # O app só vai no Google 1 vez a cada 10 minutos
def carregar_dados():
    try:
        # Carregamento em lote para economizar acessos
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        
        # Limpeza padrão
        for df in [df_b, df_j, df_a]:
            df.columns = [str(c).strip() for c in df.columns]
        
        if 'ID' in df_a.columns:
            df_a['ID'] = df_a['ID'].astype(str)
            
        return df_b, df_j, df_a
    except Exception:
        return None, None, None

# Tenta carregar os dados
df_base, df_just, df_agenda = carregar_dados()

# Se der erro de cota, mostra aviso amigável e para o código
if df_base is None:
    st.error("🚨 O Google Sheets pediu uma pausa. Aguarde 30 segundos e atualize a página.")
    st.stop()

# --- ABA LATERAL ---
menu = st.sidebar.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

if menu == "Novo Agendamento":
    st.header("📋 Novo Agendamento")
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
                
                if st.form_submit_button("💾 SALVAR"):
                    cod_c, nom_c = cliente_escolhido.split(" - ", 1)
                    novo_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    
                    nova_linha = pd.DataFrame([{"ID": novo_id, "DATA": data_visita.strftime("%d/%m/%Y"), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": justificativa_sel, "STATUS": status}])
                    
                    # Salva e LIMPA O CACHE para que a mudança apareça na hora
                    df_agenda_full = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda_full)
                    st.cache_data.clear() 
                    st.success("✅ Salvo!")
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
        st.subheader("📝 Atualizar Visita")
        dict_escolha = {f"{row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_filtrado.iterrows()}
        escolha_label = st.selectbox("Selecione:", ["Selecione..."] + list(dict_escolha.keys()))

        if escolha_label != "Selecione...":
            id_sel = dict_escolha[escolha_label]
            match = df_agenda[df_agenda['ID'] == id_sel]
            
            if not match.empty:
                dados_v = match.iloc[0]
                with st.form("form_edit"):
                    status_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    idx_s = status_list.index(dados_v['STATUS']) if dados_v['STATUS'] in status_list else 0
                    
                    just_list = list(df_just.iloc[:, 0].dropna().unique())
                    idx_j = just_list.index(dados_v['JUSTIFICATIVA']) if dados_v['JUSTIFICATIVA'] in just_list else 0

                    n_status = st.radio("Novo Status:", status_list, index=idx_s)
                    n_just = st.selectbox("Nova Justificativa:", just_list, index=idx_j)

                    if st.form_submit_button("✅ ATUALIZAR"):
                        df_agenda.loc[df_agenda['ID'] == id_sel, 'STATUS'] = n_status
                        df_agenda.loc[df_agenda['ID'] == id_sel, 'JUSTIFICATIVA'] = n_just
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                        st.cache_data.clear()
                        st.success("✅ Atualizado!")
                        st.rerun()
