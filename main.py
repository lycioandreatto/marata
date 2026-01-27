import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕", layout="centered")
st.title("📋 Agenda de Visitas - Maratá")

conn = st.connection("gsheets", type=GSheetsConnection)

# URL Principal da sua planilha
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

try:
    # 1. Carregando a aba BASE (especificando o nome exato da aba)
    # Certifique-se que o nome na aba da planilha é exatamente "BASE"
    df_base = conn.read(spreadsheet=url_planilha, worksheet="BASE", ttl=0).dropna(how='all')
    df_base.columns = [str(c).strip() for c in df_base.columns]
    
    # 2. Carregando a aba de JUSTIFICATIVAS
    # Certifique-se que o nome na aba é exatamente "JUSTIFICATIVA DE ATENDIMENTOS"
    df_just = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0).dropna(how='all')
    df_just.columns = [str(c).strip() for c in df_just.columns]

    # --- SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        # --- SELEÇÃO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            # --- SELEÇÃO DE JUSTIFICATIVA ---
            # Aqui pegamos os dados da coluna correta
            col_nome_just = 'JUSTIFICATIVA DE ATENDIMENTOS'
            
            # Se a coluna existir, usa ela. Se não, pega a primeira coluna disponível na aba de justificativas
            if col_nome_just in df_just.columns:
                opcoes_just = df_just[col_nome_just].dropna().unique()
            else:
                opcoes_just = df_just.iloc[:, 0].dropna().unique()
            
            with st.form("form_registro"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa_sel = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                if st.form_submit_button("💾 SALVAR NA AGENDA"):
                    cod_c, nom_c = cliente_escolhido.split(" - ", 1)

                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_visita.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_c,
                        "CLIENTE": nom_c,
                        "JUSTIFICATIVA": justificativa_sel,
                        "STATUS": status
                    }])

                    # Lê a aba AGENDA e salva
                    df_agenda_atual = conn.read(spreadsheet=url_planilha, worksheet="AGENDA", ttl=0)
                    df_final = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                    
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    
                    st.success("✅ Salvo com sucesso na aba AGENDA!")
                    st.balloons()

except Exception as e:
    st.error(f"Erro detectado: {e}")
    st.info("Dica: Verifique se os nomes das abas na sua planilha são exatamente: BASE, JUSTIFICATIVA DE ATENDIMENTOS e AGENDA.")
