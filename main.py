import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Agenda Maratá", page_icon="☕", layout="centered")

st.title("📋 Agenda de Visitas - Maratá")

# Conexão autenticada (usando seus Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

# URLs das abas
url_base = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=0#gid=0"
url_just = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=737114512#gid=737114512"
url_agen = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=1524427885#gid=1524427885"

try:
    # Carregando os dados iniciais
    df_base = conn.read(spreadsheet=url_base, ttl=0).dropna(how='all')
    df_just = conn.read(spreadsheet=url_just, ttl=0).dropna(how='all')
    
    # Limpeza de colunas
    df_base.columns = [str(c).strip() for c in df_base.columns]
    df_just.columns = [str(c).strip() for c in df_just.columns]

    # --- 1. SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        # --- 2. SELEÇÃO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            # --- 3. FORMULÁRIO DE REGISTRO ---
            opcoes_just = df_just['JUSTIFICATIVA DE ATENDIMENTOS'].dropna().unique()
            
            with st.form("form_final"):
                st.info(f"Registrando visita para: {cliente_escolhido}")
                
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                if st.form_submit_button("💾 SALVAR NA AGENDA"):
                    # Extrair código e nome
                    cod_c, nom_c = cliente_escolhido.split(" - ", 1)

                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_visita.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_c,
                        "CLIENTE": nom_c,
                        "JUSTIFICATIVA": justificativa,
                        "STATUS": status
                    }])

                    # Adiciona na aba AGENDA
                    df_agenda = conn.read(spreadsheet=url_agen, ttl=0)
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    
                    conn.update(spreadsheet=url_agen, data=df_final)
                    st.success("✅ Registro salvo com sucesso na aba AGENDA!")
                    st.balloons()

except Exception as e:
    st.error(f"Ocorreu um erro: {e}")
