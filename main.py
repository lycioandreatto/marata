import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

@st.cache_data(ttl=600)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_j.columns = [str(c).strip() for c in df_j.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
        
        if 'ID' in df_a.columns:
            df_a['ID'] = df_a['ID'].astype(str)
            
        return df_b, df_j, df_a
    except Exception:
        return None, None, None

df_base, df_just, df_agenda = carregar_dados()

if df_base is None:
    st.error("🚨 Limite do Google atingido. Aguarde 30 segundos e atualize.")
    st.stop()

menu = st.sidebar.selectbox("Navegação", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

if menu == "Novo Agendamento":
    st.header("📋 Planejar Nova Visita")
    col_sup_nome = 'Região de vendas'
    supervisores = sorted([s for s in df_base[col_sup_nome].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        clientes_filtrados = df_base[df_base[col_sup_nome] == sup_sel]
        lista_clientes = sorted(clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_clientes)

        if cliente_escolhido != "Selecione...":
            opcoes_just = df_just.iloc[:, 0].dropna().unique()
            with st.form("form_novo"):
                status = st.radio("Status:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa_sel = st.selectbox("Justificativa:", list(opcoes_just))
                data_visita = st.date_input("Data:", datetime.now())
                
                if st.form_submit_button("💾 SALVAR"):
                    cod_c, nom_c = cliente_escolhido.split(" - ", 1)
                    novo_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    nova_linha = pd.DataFrame([{"ID": novo_id, "DATA": data_visita.strftime("%d/%m/%Y"), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": justificativa_sel, "STATUS": status}])
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Salvo!")
                    st.rerun()

elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda Organizada")
    
    if not df_agenda.empty:
        # --- LÓGICA DE ORDENAÇÃO POR DATA ---
        # 1. Converte a coluna DATA de texto para formato de data real para o Python entender a ordem
        df_agenda['DATA_OBJ'] = pd.to_datetime(df_agenda['DATA'], format='%d/%m/%Y', errors='coerce')
        
        # 2. Organiza (Sort) pela data (mais próxima primeiro)
        df_agenda = df_agenda.sort_values(by='DATA_OBJ', ascending=True)

        supervisores_agenda = sorted(df_agenda['SUPERVISOR'].unique())
        filtro_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + supervisores_agenda)
        
        df_filtrado = df_agenda.copy()
        if filtro_sup != "Todos":
            df_filtrado = df_filtrado[df_filtrado['SUPERVISOR'] == filtro_sup]

        # Remove colunas auxiliares e ID da visão do usuário
        cols_visiveis = [c for c in df_filtrado.columns if c not in ['ID', 'DATA_OBJ']]
        st.dataframe(df_filtrado[cols_visiveis], use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Atualizar Registro")
        # No seletor de edição, as opções também aparecerão em ordem cronológica agora
        dict_labels = {f"{row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_filtrado.iterrows()}
        escolha_edit = st.selectbox("Escolha a visita:", ["Selecione..."] + list(dict_labels.keys()))

        if escolha_edit != "Selecione...":
            id_sel = dict_labels[escolha_edit]
            match = df_agenda[df_agenda['ID'] == id_sel]
            if not match.empty:
                dados_v = match.iloc[0]
                with st.form("form_edit"):
                    st.write(f"Editando: **{dados_v['CLIENTE']}**")
                    st_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    idx_s = st_list.index(dados_v['STATUS']) if dados_v['STATUS'] in st_list else 0
                    ju_list = list(df_just.iloc[:, 0].dropna().unique())
                    idx_j = ju_list.index(dados_v['JUSTIFICATIVA']) if dados_v['JUSTIFICATIVA'] in ju_list else 0

                    novo_st = st.radio("Status:", st_list, index=idx_s, horizontal=True)
                    nova_ju = st.selectbox("Justificativa:", ju_list, index=idx_j)

                    if st.form_submit_button("✅ ATUALIZAR"):
                        # Atualiza no dataframe original (sem a coluna temporária DATA_OBJ)
                        df_save = df_agenda.drop(columns=['DATA_OBJ'])
                        df_save.loc[df_save['ID'] == id_sel, 'STATUS'] = novo_st
                        df_save.loc[df_save['ID'] == id_sel, 'JUSTIFICATIVA'] = nova_ju
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save)
                        st.cache_data.clear()
                        st.success("✅ Atualizado!")
                        st.rerun()
    else:
        st.info("Agenda vazia.")
