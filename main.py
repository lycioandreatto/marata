import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

def preparar_df(df):
    # Remove colunas sem nome (Unnamed) e espaços nos títulos
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.strip()
    return df

try:
    # Lendo as abas
    df_base = preparar_df(conn.read(spreadsheet=url, worksheet="Planilha1", ttl=0))
    df_just = preparar_df(conn.read(spreadsheet=url, worksheet="Planilha2", ttl=0))
    
    # SELEÇÃO DE SUPERVISOR
    col_sup = 'Região de vendas'
    supervisores = sorted(df_base[col_sup].dropna().unique())
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(supervisores))

    if sup_sel != "Selecione...":
        # FILTRO DE CLIENTE
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            # JUSTIFICATIVAS
            col_just = 'JUSTIFICATIVA DE ATENDIMENTOS'
            opcoes_just = df_just[col_just].dropna().unique()
            
            with st.form("registro_visita"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                data_sel = st.date_input("DATA DA VISITA:", datetime.now())
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    cod_cliente = cliente_escolhido.split(" - ")[0]
                    nome_cliente = cliente_escolhido.split(" - ")[1]

                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_sel.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_cliente,
                        "CLIENTE": nome_cliente,
                        "JUSTIFICATIVA": justificativa,
                        "STATUS": status
                    }])

                    # Tenta ler a Planilha3, se falhar ou estiver vazia, cria uma nova
                    try:
                        df_agenda = conn.read(spreadsheet=url, worksheet="Planilha3", ttl=0)
                        df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    except:
                        df_final = nova_linha

                    conn.update(spreadsheet=url, worksheet="Planilha3", data=df_final)
                    st.success("✅ Visita registrada na Planilha3!")
                    st.balloons()

except Exception as e:
    st.error(f"Erro: {e}")
