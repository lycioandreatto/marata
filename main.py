import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

# --- FUNÇÕES DE CARREGAMENTO ---
def carregar_dados():
    df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE", ttl=0).dropna(how='all')
    df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0).dropna(how='all')
    df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA", ttl=0).dropna(how='all')
    
    for df in [df_b, df_j, df_a]:
        df.columns = [str(c).strip() for c in df.columns]
    return df_b, df_j, df_a

df_base, df_just, df_agenda = carregar_dados()

# --- NAVEGAÇÃO ---
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
                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_visita.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_c,
                        "CLIENTE": nom_c,
                        "JUSTIFICATIVA": justificativa_sel,
                        "STATUS": status
                    }])
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.success("✅ Agendado!")
                    st.balloons()

elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    
    # Filtro de Supervisor para ver a agenda específica
    supervisores_agenda = sorted(df_agenda['SUPERVISOR'].unique())
    filtro_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + supervisores_agenda)
    
    df_filtrado = df_agenda.copy()
    if filtro_sup != "Todos":
        df_filtrado = df_filtrado[df_filtrado['SUPERVISOR'] == filtro_sup]

    # Exibe a tabela
    st.dataframe(df_filtrado, use_container_width=True)

    st.markdown("---")
    st.subheader("📝 Atualizar Status de Visita")
    
    # Selecionar uma visita pelo ID ou Cliente para editar
    if not df_filtrado.empty:
        # Criamos uma lista de opções amigável: "Data - Cliente (ID)"
        opcoes_edicao = df_filtrado.apply(lambda x: f"{x['DATA']} - {x['CLIENTE']} (ID:{x['ID']})", axis=1).tolist()
        visita_para_editar = st.selectbox("Selecione a visita que deseja atualizar:", ["Selecione..."] + opcoes_edicao)

        if visita_para_editar != "Selecione...":
            # Extrair o ID da string selecionada
            id_sel = visita_para_editar.split("(ID:")[1].replace(")", "")
            
            # Pegar os dados atuais dessa visita
            dados_visita = df_agenda[df_agenda['ID'] == id_sel].iloc[0]
            
            with st.form("form_edicao"):
                st.write(f"Atualizando: **{dados_visita['CLIENTE']}**")
                novo_status = st.radio("Mudar Status para:", ("Planejado (X)", "Realizado", "Reagendado"), 
                                       index=("Planejado (X)", "Realizado", "Reagendado").index(dados_visita['STATUS']))
                
                nova_just = st.selectbox("Nova Justificativa:", list(df_just.iloc[:, 0].dropna().unique()),
                                         index=list(df_just.iloc[:, 0].dropna().unique()).index(dados_visita['JUSTIFICATIVA']) if dados_visita['JUSTIFICATIVA'] in list(df_just.iloc[:, 0].dropna().unique()) else 0)

                if st.form_submit_button("✅ ATUALIZAR REGISTRO"):
                    # Localizar a linha exata no DataFrame original e atualizar
                    df_agenda.loc[df_agenda['ID'] == id_sel, 'STATUS'] = novo_status
                    df_agenda.loc[df_agenda['ID'] == id_sel, 'JUSTIFICATIVA'] = nova_just
                    
                    # Salvar a planilha inteira atualizada
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                    st.success("✅ Registro atualizado na planilha!")
                    st.rerun()
    else:
        st.warning("Nenhuma visita encontrada para este supervisor.")
