import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Tenta carregar a BASE
    # Se der erro 400 aqui, ele vai para o except e nos mostra os nomes reais das abas
    df_base = conn.read(spreadsheet=url, worksheet="BASE", ttl=0)
    df_just = conn.read(spreadsheet=url, worksheet="JUSTIFICATIVA DE ATENDIMENTOS", ttl=0)
    
    st.success("Conectado à planilha!")

    # --- SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    if col_sup in df_base.columns:
        supervisores = sorted(df_base[col_sup].dropna().unique())
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(supervisores))
    else:
        st.error(f"Coluna '{col_sup}' não encontrada na aba BASE. Colunas: {list(df_base.columns)}")
        st.stop()

    if sup_sel != "Selecione...":
        # --- FILTRO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        lista_exibicao = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_exibicao))

        if cliente_escolhido != "Selecione...":
            cod_cliente = cliente_escolhido.split(" - ")[0]
            nome_cliente = cliente_escolhido.split(" - ")[1]

            # --- JUSTIFICATIVAS ---
            opcoes_just = df_just['JUSTIFICATIVA DE ATENDIMENTOS'].dropna().unique()
            
            with st.form("form_agenda"):
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", opcoes_just)
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_visita.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_cliente,
                        "CLIENTE": nome_cliente,
                        "JUSTIFICATIVA": justificativa,
                        "STATUS": status
                    }])

                    df_agenda_atual = conn.read(spreadsheet=url, worksheet="AGENDA", ttl=0)
                    df_atualizado = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="AGENDA", data=df_atualizado)
                    
                    st.success("✅ Gravado com sucesso na aba AGENDA!")
                    st.balloons()

except Exception as e:
    st.error(f"Erro detalhado: {e}")
    st.info("💡 Dica: Verifique se os nomes das abas na planilha são exatamente: BASE, AGENDA, JUSTIFICATIVA DE ATENDIMENTOS. Sem espaços antes ou depois.")
