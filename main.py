import streamlit as st
from streamlit_gsheets import GSheetsConnection
import traceback

st.set_page_config(page_title="Debug Maratá")
st.title("Depurador de Conexão")

try:
    # Tenta conectar
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Tenta ler a aba BASE
    url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
    df = conn.read(spreadsheet=url, worksheet="BASE", ttl=0)
    
    st.success("Conectado!")
    st.dataframe(df.head())

except Exception:
    # Isso aqui vai forçar o erro a aparecer na tela
    st.error("Erro detectado!")
    st.text(traceback.format_exc())
