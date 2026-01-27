import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Tentativa 1: Ler todas as abas de uma vez para ver o que o Google entrega
    # Se o nome falhar, o Streamlit tenta carregar a primeira aba padrão
    df_base = conn.read(spreadsheet=url, worksheet="BASE", ttl=0).fillna("")
    df_just = conn.read(spreadsheet=url, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0).fillna("")
    
    st.sidebar.success("Conexão estabelecida!")

    # --- SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    if col_sup in df_base.columns:
        supervisores = sorted([s for s in df_base[col_sup].unique() if s])
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)
    else:
        st.error(f"Coluna '{col_sup}' não encontrada.")
        st.write("Colunas reais na aba BASE:", list(df_base.columns))
        st.stop()

    if sup_sel != "Selecione...":
        # --- FILTRO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        
        # Montando a lista de seleção
        # Usamos .get() para evitar erro se a coluna sumir
        lista_exibicao = []
        for _, row in clientes_filtrados.iterrows():
            lista_exibicao.append(f"{row['Cliente']} - {row['Nome 1']}")
        
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_exibicao))

        if cliente_escolhido != "Selecione...":
            partes = cliente_escolhido.split(" - ")
            cod_cliente = partes[0]
            nome_cliente = partes[1]

            # --- JUSTIFICATIVAS ---
            col_just = 'JUSTIFICATIVA DE ATENDIMENTOS'
            opcoes_just = sorted([j for j in df_just[col_just].unique() if j])
            
            with st.form("form_agenda"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", ["Selecione..."] + opcoes_just)
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    if justificativa == "Selecione...":
                        st.warning("Por favor, selecione uma justificativa.")
                    else:
                        # Criar nova linha
                        nova_linha = pd.DataFrame([{
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "DATA": data_visita.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO CLIENTE": cod_cliente,
                            "CLIENTE": nome_cliente,
                            "JUSTIFICATIVA": justificativa,
                            "STATUS": status
                        }])

                        # Gravar na aba AGENDA
                        df_agenda_atual = conn.read(spreadsheet=url, worksheet="AGENDA", ttl=0)
                        df_atualizado = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url, worksheet="AGENDA", data=df_atualizado)
                        
                        st.success("✅ Registro salvo na aba AGENDA!")
                        st.balloons()

except Exception as e:
    st.error(f"Erro Crítico: {e}")
    st.write("DICA: Tente renomear as abas para nomes simples (ex: Planilha1) para testar.")
