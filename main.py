import streamlit as st
from geopy.geocoders import Nominatim # Para pegar localização se quiser
import pandas as pd
from gsheetsdb import connect

# 1. Configuração da Página
st.set_page_config(page_title="Agenda Maratá", layout="centered")

st.title("📋 Agenda de Visitas - Maratá")

# 2. Conexão com sua Planilha Google (Substitua pelo seu link)
sheet_url = "SUA_PLANILHA_GOOGLE_AQUI"
conn = connect()

def run_query(query):
    rows = conn.execute(query, headers=1)
    return pd.DataFrame(rows)

# 3. Login Simples
vendedor = st.selectbox("Selecione seu nome:", ["João Silva", "Maria Souza", "José Carlos"])

if vendedor:
    st.subheader(f"Clientes de Hoje - {vendedor}")
    
    # Simulação de dados (Aqui ele leria do seu Google Sheets)
    # Na prática, usaríamos df = run_query(f"SELECT * FROM '{sheet_url}' WHERE Supervisor = '{vendedor}'")
    
    # 4. Interface de Check-in
    cliente = st.selectbox("Selecione o Cliente para Visita:", ["Supermercado X", "Atacadista Y", "Mercadinho Z"])
    
    status = st.radio("Status da Visita:", ("Planejado (X)", "Realizado", "Reagendado"))
    
    justificativa = ""
    if status == "Reagendado":
        justificativa = st.text_input("Motivo do Reagendamento:")

    if st.button("Salvar Visita"):
        # Aqui entra o código para gravar na planilha
        st.success(f"Visita ao cliente {cliente} salva com sucesso!")
        st.balloons()
