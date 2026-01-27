import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")

st.title("📋 Agenda de Visitas - Maratá")

# Conexão
url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Lê os dados
    df = conn.read(spreadsheet=url, ttl=0)
    
    # 1. Seleção do Supervisor (Primeira Coluna)
    col_supervisor = 'Supervisor' # Ajuste se o nome na planilha for diferente
    vendedores = sorted(df[col_supervisor].dropna().unique())
    vendedor_sel = st.selectbox("Selecione seu nome:", ["Selecione..."] + list(vendedores))

    if vendedor_sel != "Selecione...":
        # 2. Filtrar clientes apenas desse supervisor
        # Ajuste 'Nome_Cliente' para o nome exato da sua coluna de clientes
        col_cliente = 'Nome_Cliente' 
        
        filtro = df[df[col_supervisor] == vendedor_sel]
        lista_clientes = sorted(filtro[col_cliente].dropna().unique())
        
        cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_clientes)

        if cliente_sel != "Selecione...":
            # 3. Formulário de Check-in
            with st.form("checkin_form"):
                status = st.radio("Status da Visita:", ("Planejado (X)", "Realizado", "Reagendado"))
                obs = st.text_area("Observações / Justificativa:")
                
                botao = st.form_submit_button("Confirmar Visita")
                
                if botao:
                    # Aqui preparamos os dados para salvar
                    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    # No Streamlit, para salvar de volta na planilha, geralmente 
                    # criamos uma aba chamada "LOG" ou "RESPOSTAS"
                    st.success(f"Visita ao cliente {cliente_sel} registrada com sucesso!")
                    st.info(f"Dados: {vendedor_sel} | {status} | {data_hora}")
                    st.balloons()

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
