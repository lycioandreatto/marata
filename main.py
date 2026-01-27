import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
import pytz

# 1. Configuração da Página
st.set_page_config(page_title="Gestão Maratá - Admin", page_icon="☕", layout="wide")

# 2. Conexão e Fuso
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

# --- ESTADO DE SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_nome' not in st.session_state:
    st.session_state.usuario_nome = ""

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=10)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        for df in [df_b, df_j, df_a, df_u]:
            df.columns = [str(c).strip() for c in df.columns]
        df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except: return None, None, None, None

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- TELA DE ACESSO ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.title("☕ MARATÁ")
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema", use_container_width=True):
            if df_usuarios is not None and not df_usuarios.empty:
                # Verificação ignorando maiúsculas/minúsculas no login
                match = df_usuarios[(df_usuarios['USUARIO'].str.lower() == u.lower()) & (df_usuarios['SENHA'].astype(str) == s)]
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario_nome = match.iloc[0]['USUARIO']
                    st.rerun()
                else: st.error("Incorreto.")
    st.stop()

# --- LÓGICA DE ADMIN (FORÇADA) ---
# Aqui definimos que "Lycio" (independente de maiúscula) é o dono
usuario_atual = st.session_state.usuario_nome
eh_admin = usuario_atual.lower() == "lycio"

# --- ÁREA LOGADA ---
with st.sidebar:
    st.subheader("☕ Gestão Maratá")
    if eh_admin:
        st.write("⭐ **MODO ADMINISTRADOR**")
        st.info(f"Bem-vindo, {usuario_atual}")
    else:
        st.write(f"👤 Supervisor: {usuario_atual}")
    
    st.markdown("---")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Visualizar Agenda"])
    
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# 1. NOVO AGENDAMENTO
if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    
    if eh_admin:
        # Se é ADM, ele PRECISA escolher um supervisor antes
        lista_supervisores = sorted([s for s in df_base['Região de vendas'].unique() if str(s).strip() and str(s) != 'nan'])
        sup_alvo = st.selectbox("Selecionar Supervisor para Agendar:", ["Selecione..."] + lista_supervisores)
    else:
        sup_alvo = usuario_atual

    if sup_alvo != "Selecione...":
        clientes_f = df_base[df_base['Região de vendas'] == sup_alvo]
        
        if clientes_f.empty:
            st.warning(f"Não há clientes mapeados para '{sup_alvo}' na base.")
        else:
            lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            cliente_sel = st.selectbox("Escolher Cliente:", ["Selecione..."] + lista_c)
            
            if cliente_sel != "Selecione...":
                with st.form("form_novo"):
                    data_v = st.date_input("Data:", datetime.now(fuso_br))
                    if st.form_submit_button("💾 SALVAR"):
                        cod_c, nom_c = cliente_sel.split(" - ", 1)
                        agora = datetime.now(fuso_br)
                        novo_id = agora.strftime("%Y%m%d%H%M%S")
                        nova_linha = pd.DataFrame([{"ID": novo_id, "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), "DATA": data_v.strftime("%d/%m/%Y"), "SUPERVISOR": sup_alvo, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)"}])
                        df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                        st.cache_data.clear()
                        st.success("Agendado!")
                        st.rerun()

# 2. VISUALIZAR AGENDA
elif menu == "Visualizar Agenda":
    st.header("🔍 Agenda de Visitas")
    
    if eh_admin:
        # Admin vê filtro de todos
        sups_na_agenda = sorted(df_agenda['SUPERVISOR'].unique().tolist())
        f_sup = st.selectbox("Filtrar Visão (ADM):", ["Todos"] + sups_na_agenda)
        df_exibir = df_agenda.copy()
        if f_sup != "Todos":
            df_exibir = df_exibir[df_exibir['SUPERVISOR'] == f_sup]
    else:
        # Supervisor só vê o dele
        df_exibir = df_agenda[df_agenda['SUPERVISOR'] == usuario_atual].copy()

    if df_exibir.empty:
        st.info("Nada encontrado.")
    else:
        # Tabela e Edição seguem o fluxo normal
        st.dataframe(df_exibir[['DATA', 'SUPERVISOR', 'CLIENTE', 'STATUS']], use_container_width=True)
        # (Aqui você pode manter seu código de edição via checkbox se desejar)
