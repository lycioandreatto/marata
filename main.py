import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Agenda Maratá", page_icon="☕", layout="centered")

st.title("📋 Agenda de Visitas - Maratá")

# Inicializa a conexão
# O nome "gsheets" deve bater com o [connections.gsheets] nos Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# URLs das abas usando o GID para precisão total
url_base = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=0#gid=0"
url_just = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=737114512#gid=737114512"
url_agen = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit?gid=1524427885#gid=1524427885"

def carregar_dados():
    try:
        # Lê os dados (usa autenticação se configurada corretamente nos Secrets)
        df_b = conn.read(spreadsheet=url_base, ttl=0).dropna(how='all')
        df_j = conn.read(spreadsheet=url_just, ttl=0).dropna(how='all')
        
        # Limpa espaços nos nomes das colunas
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_j.columns = [str(c).strip() for c in df_j.columns]
        
        return df_b, df_j
    except Exception as e:
        st.error(f"Erro ao carregar abas: {e}")
        return None, None

df_base, df_just = carregar_dados()

if df_base is not None and df_just is not None:
    # --- SELEÇÃO DE SUPERVISOR ---
    col_sup = 'Região de vendas'
    if col_sup in df_base.columns:
        supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip() and s != 'nan'])
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

        if sup_sel != "Selecione...":
            # --- SELEÇÃO DE CLIENTE ---
            clientes_filtrados = df_base[df_base[col_sup] == sup_sel]
            # Formata lista: Código - Nome
            lista_clientes = clientes_filtrados.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist()
            cliente_escolhido = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))

            if cliente_escolhido != "Selecione...":
                # --- FORMULÁRIO DE REGISTRO ---
                col_just_nome = 'JUSTIFICATIVA DE ATENDIMENTOS'
                opcoes_just = df_just[col_just_nome].dropna().unique()
                
                with st.form("registro_marata"):
                    st.subheader("Registrar Atendimento")
                    
                    status = st.radio("STATUS:", ("Planejado (X)", "Realizado", "Reagendado"))
                    justificativa = st.selectbox("JUSTIFICATIVA:", list(opcoes_just))
                    data_visita = st.date_input("DATA DA VISITA:", datetime.now())
                    
                    btn_salvar = st.form_submit_button("💾 SALVAR NA AGENDA")

                    if btn_salvar:
                        # Extrair Código e Nome
                        cod_c, nom_c = cliente_escolhido.split(" - ", 1)

                        # Criar linha para salvar
                        nova_visita = pd.DataFrame([{
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "DATA": data_visita.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO CLIENTE": cod_c,
                            "CLIENTE": nom_c,
                            "JUSTIFICATIVA": justificativa,
                            "STATUS": status
                        }])

                        try:
                            # 1. Busca a agenda atual
                            df_agenda_atual = conn.read(spreadsheet=url_agen, ttl=0)
                            # 2. Une com a nova linha
                            df_final = pd.concat([df_agenda_atual, nova_visita], ignore_index=True)
                            # 3. Faz o Update (Escrita)
                            conn.update(spreadsheet=url_agen, data=df_final)
                            
                            st.success("✅ Visita registrada com sucesso na aba AGENDA!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                            st.info("Verifique se o e-mail da conta de serviço está como EDITOR na planilha.")
    else:
        st.error(f"Coluna '{col_sup}' não encontrada. Verifique o cabeçalho da aba BASE.")

# Rodapé informativo
st.markdown("---")
st.caption("Sistema de Agenda Maratá - Conexão Segura via Google Service Account")
