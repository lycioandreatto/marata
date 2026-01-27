import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# FUNÇÃO PARA LIMPAR NOMES DE COLUNAS
def limpar_df(df):
    df.columns = df.columns.str.strip()
    return df

try:
    # Tenta ler a aba BASE
    # Se der erro aqui, vamos capturar o motivo real
    df_base = conn.read(spreadsheet=url, worksheet="BASE", ttl=0)
    df_base = limpar_df(df_base)
    
    df_just = conn.read(spreadsheet=url, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0)
    df_just = limpar_df(df_just)

    # --- SELEÇÃO DE SUPERVISOR ---
    # Usando o nome da coluna que você passou
    col_sup = 'Região de vendas'
    
    if col_sup in df_base.columns:
        supervisores = sorted(df_base[col_sup].dropna().unique())
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(supervisores))
    else:
        st.error(f"Não achei a coluna '{col_sup}'.")
        st.write("Colunas que achei na aba BASE:", list(df_base.columns))
        st.stop()

    if sup_sel != "Selecione...":
        # --- FILTRO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        
        # Criando a lista de seleção
        lista_exibicao = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_exibicao))

        if cliente_escolhido != "Selecione...":
            cod_cliente = cliente_escolhido.split(" - ")[0]
            nome_cliente = cliente_escolhido.split(" - ")[1]

            # --- JUSTIFICATIVAS ---
            opcoes_just = df_just['JUSTIFICATIVA DE ATENDIMENTOS'].dropna().unique()
            
            with st.form("form_agenda"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", ["Selecione..."] + list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    if justificativa == "Selecione...":
                        st.warning("Selecione uma justificativa!")
                    else:
                        # Dados para salvar
                        nova_linha = pd.DataFrame([{
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "DATA": data_visita.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO CLIENTE": cod_cliente,
                            "CLIENTE": nome_cliente,
                            "JUSTIFICATIVA": justificativa,
                            "STATUS": status
                        }])

                        # Grava na aba AGENDA
                        df_agenda_atual = conn.read(spreadsheet=url, worksheet="AGENDA", ttl=0)
                        df_atualizado = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url, worksheet="AGENDA", data=df_atualizado)
                        
                        st.success("✅ Gravado com sucesso na aba AGENDA!")
                        st.balloons()

except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.write("Verifique se as abas se chamam exatamente: BASE, AGENDA e JUSTIFICATIVA DE ATENDIMENTOS (sem espaços extras)")
