import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Agenda Maratá", page_icon="☕", layout="centered")

st.title("📋 Agenda de Visitas - Maratá")

# CONFIGURAÇÃO DA CONEXÃO: 
# Ao usar "gsheets", ele busca automaticamente nos Secrets [connections.gsheets]
conn = st.connection("gsheets", type=GSheetsConnection)

# Links das abas (usados para leitura e identificação)
url_base = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=0#gid=0"
url_just = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=737114512#gid=737114512"
url_agen = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=1524427885#gid=1524427885"

try:
    # 1. Leitura dos Dados
    df_base = conn.read(spreadsheet=url_base, ttl=0).dropna(how='all')
    df_just = conn.read(spreadsheet=url_just, ttl=0).dropna(how='all')
    
    # Limpeza básica de nomes de colunas
    df_base.columns = [str(c).strip() for c in df_base.columns]
    df_just.columns = [str(c).strip() for c in df_just.columns]

    # --- SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    if col_sup in df_base.columns:
        supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip()])
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)
    else:
        st.error(f"Coluna '{col_sup}' não encontrada na aba BASE.")
        st.stop()

    if sup_sel != "Selecione...":
        # --- FILTRO DE CLIENTE ---
        clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
        lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
        cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

        if cliente_escolhido != "Selecione...":
            # --- JUSTIFICATIVAS ---
            col_just_nome = 'JUSTIFICATIVA DE ATENDIMENTOS'
            opcoes_just = df_just[col_just_nome].dropna().unique()
            
            with st.form("form_registro"):
                st.subheader(f"Visita: {cliente_escolhido}")
                
                status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                justificativa = st.selectbox("JUSTIFICATIVA:", ["Selecione..."] + list(opcoes_just))
                data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                
                salvar = st.form_submit_button("💾 SALVAR NA AGENDA")

                if salvar:
                    if justificativa == "Selecione...":
                        st.warning("Por favor, escolha uma justificativa.")
                    else:
                        # Extrair Código e Nome
                        partes = cliente_escolhido.split(" - ", 1)
                        cod_c = partes[0]
                        nom_c = partes[1]

                        # Criar Nova Linha
                        nova_linha = pd.DataFrame([{
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "DATA": data_visita.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO CLIENTE": cod_c,
                            "CLIENTE": nom_c,
                            "JUSTIFICATIVA": justificativa,
                            "STATUS": status
                        }])

                        # Tenta ler a AGENDA atual e concatenar
                        try:
                            df_agenda_atual = conn.read(spreadsheet=url_agen, ttl=0)
                            df_final = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
                        except:
                            df_final = nova_linha # Se falhar a leitura, inicia a tabela com a nova linha

                        # ENVIO DOS DADOS (Necessita autenticação de Service Account)
                        conn.update(spreadsheet=url_agen, data=df_final)
                        
                        st.success("✅ Dados gravados com sucesso na aba AGENDA!")
                        st.balloons()

except Exception as e:
    st.error(f"Erro detalhado: {e}")
    st.info("💡 Lembrete: O e-mail da conta de serviço deve ser EDITOR na planilha.")
