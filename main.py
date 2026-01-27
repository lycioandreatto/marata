import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Agenda Maratá", layout="centered")
st.title("📋 Agenda de Visitas - Maratá")

# Link direto da sua planilha
url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Lendo os dados passando a URL diretamente
    df = conn.read(spreadsheet=url, ttl=0)
    
    if not df.empty:
        # Tenta encontrar a coluna de Supervisor
        colunas = list(df.columns)
        st.write("Conectado com sucesso!")
        
        # Se você souber o nome da coluna, troque 'Supervisor' abaixo
        vendedor_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(df.iloc[:, 0].unique())) 
    else:
        st.warning("A planilha foi lida, mas parece estar vazia.")

except Exception as e:
    st.error(f"Erro na conexão: {e}")
