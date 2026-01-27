import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agenda Maratá", page_icon="☕")
st.title("📋 Agenda de Visitas - Maratá")

url = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_colunas(df):
    df.columns = df.columns.str.strip()
    return df

try:
    # 1. Carregar Dados
    # Planilha1 = BASE | Planilha2 = JUSTIFICATIVAS | Planilha3 = AGENDA
    df_base = limpar_colunas(conn.read(spreadsheet=url, worksheet="Planilha1", ttl=0))
    df_just = limpar_colunas(conn.read(spreadsheet=url, worksheet="Planilha2", ttl=0))
    
    # 2. Seleção de Supervisor
    # Usando o nome da coluna que você informou: 'Região de vendas'
    supervisores = sorted(df_base['Região de vendas'].dropna().unique())
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + list(supervisores))

    if sup_sel != "Selecione...":
        # 3. Filtrar Clientes
        clientes_filtrados = df_base[df_base['Região de vendas'] == sup_sel]
        
        # Criando a lista combinada: Código - Nome
        lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            # 4. Formulário de Registro
            # Puxa as opções da Planilha2
            opcoes_just = df_just['JUSTIFICATIVA DE ATENDIMENTOS'].dropna().unique()
            
            with st.form("registro_visita"):
                st.write(f"### Registro para: {cliente_escolhido}")
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                data_sel = st.date_input("DATA DA VISITA:", datetime.now())
                
                submit = st.form_submit_button("SALVAR NA AGENDA")

                if submit:
                    # Preparar os dados para salvar na Planilha3
                    cod_cliente = cliente_escolhido.split(" - ")[0]
                    nome_cliente = cliente_escolhido.split(" - ")[1]

                    nova_linha = pd.DataFrame([{
                        "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "DATA": data_sel.strftime("%d/%m/%Y"),
                        "SUPERVISOR": sup_sel,
                        "CÓDIGO CLIENTE": cod_cliente,
                        "CLIENTE": nome_cliente,
                        "JUSTIFICATIVA": justificativa,
                        "STATUS": status
                    }])

                    # Lendo a agenda atual (Planilha3) e anexando a nova linha
                    df_agenda = conn.read(spreadsheet=url, worksheet="Planilha3", ttl=0)
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    
                    # Enviando de volta para o Google
                    conn.update(spreadsheet=url, worksheet="Planilha3", data=df_final)
                    
                    st.success("✅ Visita registrada com sucesso na Planilha3!")
                    st.balloons()

except Exception as e:
    st.error(f"Erro ao processar abas: {e}")
    st.info("Dica: Verifique se as abas se chamam Planilha1, Planilha2 e Planilha3 e se possuem dados.")
