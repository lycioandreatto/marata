import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

# --- FUNÇÕES DE CARREGAMENTO ---
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE", ttl=0).dropna(how='all')
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0).dropna(how='all')
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA", ttl=0).dropna(how='all')
        
        for df in [df_b, df_j, df_a]:
            df.columns = [str(c).strip() for c in df_base.columns if c in df.columns] # Fallback columns logic
            df.columns = [str(c).strip() for c in df.columns]
        
        if 'ID' in df_a.columns:
            df_a['ID'] = df_a['ID'].astype(str)
            
        return df_b, df_j, df_a
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_base, df_just, df_agenda = carregar_dados()

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
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
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

        # EXIBIÇÃO: Removemos a coluna ID apenas da visualização do usuário
        cols_para_mostrar = [c for c in df_filtrado.columns if c != 'ID']
        st.dataframe(df_filtrado[cols_para_mostrar], use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Atualizar Status")
        
        # Criamos um dicionário que guarda a label (Data - Cliente) e aponta para o ID
        dict_escolha = {f"{row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_filtrado.iterrows()}
        escolha_label = st.selectbox("Selecione a visita para atualizar:", ["Selecione..."] + list(dict_escolha.keys()))

        if escolha_label != "Selecione...":
            id_sel = dict_escolha[escolha_label] # O código recupera o ID aqui sem mostrar ao usuário
            match = df_agenda[df_agenda['ID'] == id_sel]
            
            if not match.empty:
                dados_visita = match.iloc[0]
                with st.form("form_edicao"):
                    st.write(f"Atualizando visita de: **{dados_visita['CLIENTE']}**")
                    status_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    idx_status = status_list.index(dados_visita['STATUS']) if dados_visita['STATUS'] in status_list else 0
                    
                    just_list = list(df_just.iloc[:, 0].dropna().unique())
                    idx_just = just_list.index(dados_visita['JUSTIFICATIVA']) if dados_visita['JUSTIFICATIVA'] in just_list else 0

                    novo_status = st.radio("Novo Status:", status_list, index=idx_status)
                    nova_just = st.selectbox("Nova Justificativa:", just_list, index=idx_just)

                    if st.form_submit_button("✅ ATUALIZAR"):
                        df_agenda.loc[df_agenda['ID'] == id_sel, 'STATUS'] = novo_status
                        df_agenda.loc[df_agenda['ID'] == id_sel, 'JUSTIFICATIVA'] = nova_just
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                        st.success("✅ Atualizado!")
                        st.rerun()
