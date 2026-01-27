import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Agenda Maratá", layout="centered")

st.title("📋 Agenda de Visitas - Maratá")

# Criando a conexão usando os Secrets que você já salvou
conn = st.connection("gsheets", type=GSheetsConnection)

# Lendo os dados da planilha
try:
    # O parâmetro ttl=0 evita que o app use dados antigos do "cache"
    df = conn.read(ttl=0)
    
    # Se a planilha estiver vazia ou não carregar colunas
    if df.empty:
        st.warning("A planilha parece estar vazia.")
    else:
        # Interface para o vendedor
        # AJUSTE AQUI: Use o nome exato da coluna da sua planilha (ex: 'Supervisor')
        col_vendedor = 'Supervisor' 
        
        if col_vendedor in df.columns:
            vendedores = df[col_vendedor].dropna().unique()
            vendedor_sel = st.selectbox("Selecione seu nome:", ["Selecione..."] + list(vendedores))
            
            if vendedor_sel != "Selecione...":
                st.write(f"Olá {vendedor_sel}, aqui estão seus clientes.")
        else:
            st.error(f"Coluna '{col_vendedor}' não encontrada. Colunas disponíveis: {list(df.columns)}")

except Exception as e:
    st.error(f"Erro na conexão: {e}")
