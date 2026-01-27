import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

# URL principal da planilha
url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_df(df):
    """Limpa espaços nos nomes das colunas e remove colunas vazias"""
    df.columns = [str(c).strip() for c in df.columns]
    return df

try:
    # 1. Lendo as Abas usando os nomes exatos que você confirmou
    # Se houver erro 400 aqui, o problema é o cabeçalho da planilha
    df_base = limpar_df(conn.read(spreadsheet=url, worksheet="BASE", ttl=0))
    df_just = limpar_df(conn.read(spreadsheet=url, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0))
    
    # --- SELEÇÃO DE SUPERVISOR ---
    # Coluna: Região de vendas
    col_sup = 'Região de vendas'
    supervisores = sorted([s for s in df_base[col_sup].unique() if s])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        # --- FILTRO DE CLIENTE ---
        # Colunas: Cliente (Código) e Nome 1 (Nome)
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        
        # Criando a lista combinada para o vendedor escolher
        lista_clientes = []
        for _, row in clientes_filtrados.iterrows():
            lista_clientes.append(f"{row['Cliente']} - {row['Nome 1']}")
        
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            # --- JUSTIFICATIVA ---
            # Pegando a coluna exata da aba de justificativas
            col_just_obs = 'JUSTIFICATIVA DE ATENDIMENTOS'
            opcoes_just = df_just[col_just_obs].dropna().unique()
            
            with st.form("form_visita"):
                st.info(f"Registrando visita para: {cliente_escolhido}")
                
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                if st.form_submit_button("SALVAR NA ABA AGENDA"):
                    # Separando Código e Nome
                    cod_c = cliente_escolhido.split(" - ")[0]
                    nom_c = cliente_escolhido.split(" - ")[1]

                    # Preparando a linha para salvar
                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_visita.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_c,
                        "CLIENTE": nom_c,
                        "JUSTIFICATIVA": justificativa,
                        "STATUS": status
                    }])

                    # 2. Lendo a aba AGENDA para anexar
                    df_agenda = conn.read(spreadsheet=url, worksheet="AGENDA", ttl=0)
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    
                    # 3. Atualizando a planilha
                    conn.update(spreadsheet=url, worksheet="AGENDA", data=df_final)
                    
                    st.success("✅ Visita salva com sucesso na aba AGENDA!")
                    st.balloons()

except Exception as e:
    st.error(f"Erro de Conexão ou Formato: {e}")
    st.warning("Verifique se a aba AGENDA tem os títulos na primeira linha: ID, DATA, SUPERVISOR, CÓDIGO CLIENTE, CLIENTE, JUSTIFICATIVA, STATUS")
