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
    # 1. Carregar as abas necessárias
    df_base = conn.read(spreadsheet=url, worksheet="BASE", ttl=0)
    df_just = conn.read(spreadsheet=url, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0)
    
    # 2. Seleção do Supervisor (Coluna: Região de vendas)
    supervisores = sorted(df_base['Região de vendas'].dropna().unique())
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(supervisores))

    if sup_sel != "Selecione...":
        # 3. Filtrar Clientes (Coluna: Nome 1 e Cliente para o código)
        clientes_filtrados = df_base[df_base['Região de vendas'] == sup_sel]
        # Criamos uma lista formatada "CÓDIGO - NOME" para facilitar
        lista_exibicao = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_exibicao))

        if cliente_escolhido != "Selecione...":
            # Extrair código e nome do que foi selecionado
            cod_cliente = cliente_escolhido.split(" - ")[0]
            nome_cliente = cliente_escolhido.split(" - ")[1]

            # 4. Seleção da Justificativa (Vem da aba JUSTIFICATIVA DE ATENDIMENTOS)
            opcoes_just = df_just['JUSTIFICATIVA DE ATENDIMENTOS'].dropna().unique()
            
            with st.form("form_agenda"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", opcoes_just)
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    # Preparar os dados para a aba AGENDA
                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_visita.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_cliente,
                        "CLIENTE": nome_cliente,
                        "JUSTIFICATIVA": justificativa,
                        "STATUS": status
                    }])

                    # Adicionar na aba AGENDA
                    try:
                        # Pega o que já tem na agenda e junta com o novo
                        df_agenda_atual = conn.read(spreadsheet=url, worksheet="AGENDA", ttl=0)
                        df_atualizado = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                        
                        conn.update(spreadsheet=url, worksheet="AGENDA", data=df_atualizado)
                        
                        st.success("✅ Gravado com sucesso na aba AGENDA!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao gravar: {e}")

except Exception as e:
    st.error(f"Erro ao carregar abas: {e}. Verifique se os nomes das abas (BASE, AGENDA...) estão corretos.")
