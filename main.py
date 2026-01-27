import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Diagnóstico de Conexão Maratá")

# Tenta conectar usando os Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    url_base = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=0#gid=0"
    
    st.write("Tentando ler a aba BASE...")
    df = conn.read(spreadsheet=url_base, ttl=0)
    st.success("Aba BASE carregada com sucesso!")
    st.dataframe(df.head())

except Exception as e:
    st.error(f"Erro na conexão: {e}")
    st.info("Se o erro mencionar 'Service Account', verifique se o cabeçalho nos Secrets é [connections.gsheets]")
