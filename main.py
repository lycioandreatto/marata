import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

# Link da planilha
url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. Carregando os dados das novas abas
    df_base = conn.read(spreadsheet=url, worksheet="Planilha1", ttl=0)
    df_just = conn.read(spreadsheet=url, worksheet="Planilha2", ttl=0)
    
    # Limpando espaços em branco nos nomes das colunas
    df_base.columns = df_base.columns.str.strip()
    df_just.columns = df_just.columns.str.strip()

    # --- SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    if col_sup in df_base.columns:
        supervisores = sorted(df_base[col_sup].dropna().unique())
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(supervisores))
    else:
        st.error(f"Coluna '{col_sup}' não encontrada na Planilha1.")
        st.write("Colunas detectadas:", list(df_base.columns))
        st.stop()

    if sup_sel != "Selecione...":
        # --- FILTRO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        
        # Montando a lista: Código - Nome
        lista_exibicao = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_exibicao))

        if cliente_escolhido != "Selecione...":
            cod_cliente = cliente_escolhido.split(" - ")[0]
            nome_cliente = cliente_escolhido.split(" - ")[1]

            # --- JUSTIFICATIVAS ---
            col_just = 'JUSTIFICATIVA DE ATENDIMENTOS'
            opcoes_just = df_just[col_just].dropna().unique()
            
            with st.form("form_agenda"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", ["Selecione..."] + list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    if justificativa == "Selecione...":
                        st.warning("Selecione uma justificativa!")
                    else:
                        # Criar linha para a Planilha3 (AGENDA)
                        nova_linha = pd.DataFrame([{
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "DATA": data_visita.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO CLIENTE": cod_cliente,
                            "CLIENTE": nome_cliente,
                            "JUSTIFICATIVA": justificativa,
                            "STATUS": status
                        }])

                        # Gravar na Planilha3
                        df_agenda_atual = conn.read(spreadsheet=url, worksheet="Planilha3", ttl=0)
                        df_atualizado = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url, worksheet="Planilha3", data=df_atualizado)
                        
                        st.success("✅ Registro salvo na Planilha3 (AGENDA)!")
                        st.balloons()

except Exception as e:
    st.error(f"Erro de Conexão: {e}")
