import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurações iniciais
st.set_page_config(page_title="Agenda Maratá", page_icon="☕", layout="wide")
st.title("📋 Agenda de Visitas - Maratá")

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URLs das abas da sua planilha "BASE AGENDA" 
url_base = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=0#gid=0"
url_just = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=737114512#gid=737114512"
url_agen = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=1524427885#gid=1524427885"

try:
    # 1. Lendo a aba BASE e limpando os nomes das colunas [cite: 4]
    df_base = conn.read(spreadsheet=url_base, ttl=0).dropna(how='all')
    df_base.columns = [str(c).strip() for c in df_base.columns]
    
    # 2. Lendo a aba de JUSTIFICATIVAS [cite: 4]
    df_just = conn.read(spreadsheet=url_just, ttl=0).dropna(how='all')
    df_just.columns = [str(c).strip() for c in df_just.columns]

    # --- IDENTIFICAÇÃO DINÂMICA DE COLUNAS ---
    # Identificamos as colunas pelos nomes que aparecem na sua planilha 
    col_sup = 'Região de vendas'  # Onde ficam os supervisores como RITA MARIA ou CARLOS ANTONIO
    col_cli_cod = 'Cliente'       # Código do cliente (ex: 1003505)
    col_cli_nom = 'Nome 1'        # Nome da empresa (ex: COMERCIAL THALYTA)

    if col_sup in df_base.columns:
        # Seleção de Supervisor
        supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip() and str(s) != 'nan'])
        sup_sel = st.selectbox("👤 Selecione o Supervisor:", ["Selecione..."] + supervisores)

        if sup_sel != "Selecione...":
            # Filtro de Clientes por Supervisor
            clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
            
            # Criando lista combinada: "Código - Nome"
            lista_clientes = clientes_filtrados.apply(
                lambda x: f"{x[col_cli_cod]} - {x[col_cli_nom]}", axis=1
            ).tolist()
            
            cliente_escolhido = st.selectbox("🏢 Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

            if cliente_escolhido != "Selecione...":
                # Pega as opções da primeira coluna da aba de justificativas
                col_just_opcoes = df_just.columns[0]
                opcoes_justificativa = df_just[col_just_opcoes].dropna().unique()
                
                with st.form("registro_visita"):
                    st.subheader("📝 Detalhes da Visita")
                    
                    status = st.radio("Status do Atendimento:", ("Planejado (X)", "Realizado", "Reagendado"))
                    justificativa = st.selectbox("Justificativa:", list(opcoes_justificativa))
                    data_v = st.date_input("Data:", datetime.now())
                    
                    if st.form_submit_button("💾 Salvar na Planilha"):
                        # Separando o código do nome para salvar limpo
                        cod_selecionado = cliente_escolhido.split(" - ")[0]
                        nome_selecionado = cliente_escolhido.split(" - ")[1]

                        # Criando a nova linha para a aba AGENDA
                        nova_entrada = pd.DataFrame([{
                            "DATA": data_v.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO": cod_selecionado,
                            "CLIENTE": nome_selecionado,
                            "STATUS": status,
                            "JUSTIFICATIVA": justificativa,
                            "HORA_REGISTRO": datetime.now().strftime("%H:%M:%S")
                        }])

                        # Lendo a aba AGENDA atual e adicionando a nova linha
                        df_agenda = conn.read(spreadsheet=url_agen, ttl=0)
                        df_atualizado = pd.concat([df_agenda, nova_entrada], ignore_index=True)
                        
                        # Enviando de volta para o Google Sheets
                        conn.update(spreadsheet=url_agen, data=df_atualizado)
                        
                        st.success(f"✅ Visita para {nome_selecionado} salva com sucesso!")
                        st.balloons()
    else:
        st.error(f"Erro: A coluna '{col_sup}' não foi encontrada. Colunas disponíveis: {list(df_base.columns)}")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
