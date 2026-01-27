import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Teste de Leitura: Planilha2")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Tentando ler especificamente a Planilha2
    df_just = conn.read(spreadsheet=url, worksheet="Planilha2", ttl=0)
    
    st.success("Conexão com a Planilha2 funcionou!")
    st.write("Dados da Planilha2:")
    st.dataframe(df_just)
    
    # Mostra as colunas para confirmarmos o nome exato
    st.write("Colunas detectadas na Planilha2:", list(df_just.columns))

except Exception as e:
    st.error(f"Erro ao ler Planilha2: {e}")
    st.info("Dica: Verifique se o nome da aba no Google Sheets é exatamente 'Planilha2' (com P maiúsculo e sem espaços).")
