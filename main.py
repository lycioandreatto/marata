import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("Teste de Conexão Maratá")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Tenta ler a planilha sem especificar aba (ele pega a primeira)
    df = conn.read(spreadsheet=url, ttl=0)
    st.success("Conexão básica funcionando!")
    st.write("Dados encontrados na primeira aba:")
    st.dataframe(df.head())
    
    # Lista todas as colunas para conferirmos os nomes
    st.write("Colunas detectadas:", list(df.columns))

except Exception as e:
    st.error(f"Erro persistente: {e}")
    st.info("Verifique se a aba não possui células mescladas (Merge Cells) ou se está totalmente vazia.")
