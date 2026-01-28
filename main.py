import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import io
from fpdf import FPDF
import pytz
import time
import os
from streamlit_cookies_manager import EncryptedCookieManager

# --- CONFIGURAÇÃO DE COOKIES (Lembrar Login) ---
cookies = EncryptedCookieManager(password="marata_secret_key_2026")
if not cookies.ready():
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #d3d3d3;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .user-card {
        background-color: #1e1e1e;
        padding: 12px 20px;
        border-radius: 12px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 3px 3px 10px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .user-card-text { color: white; font-weight: bold; font-size: 1.1em; }
    .user-card-icon { font-size: 1.5em; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO E CONFIGURAÇÕES ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

NOME_ADMIN = "LYCIO"
NOME_ANALISTA = "BARBARA"
NOME_DIRETORIA = "ALDO"

# --- FUNÇÕES AUXILIARES ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def gerar_pdf(df, tipo_relatorio="GERAL"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    df_pdf = df.copy()
    pdf.set_font("Arial", 'B', 12)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 8, f"Relatorio Marata - {tipo_relatorio} - {data_geracao}", ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 7)
    cols = df_pdf.columns.tolist()
    for col in cols:
        pdf.cell(30, 7, str(col)[:15], border=1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 6)
    for _, row in df_pdf.iterrows():
        for item in row:
            pdf.cell(30, 6, str(item)[:20].encode('latin-1', 'replace').decode('latin-1'), border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        df_u.columns = [str(c).strip().upper() for c in df_u.columns]
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
        
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except Exception:
        return None, None, None, pd.DataFrame(columns=["USUARIO", "SENHA"])

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- LOGIN ---
if "logado" not in st.session_state:
    if "user_marata" in cookies:
        st.session_state.logado, st.session_state.usuario = True, cookies["user_marata"]
    else:
        st.session_state.logado, st.session_state.usuario = False, ""

if not st.session_state.logado:
    st.title("☕ Acesso Gestão Maratá")
    t1, t2 = st.tabs(["Login", "Cadastro"])
    with t1:
        with st.form("l"):
            u, p = st.text_input("Usuário:").upper(), st.text_input("Senha:", type="password")
            lembrar = st.checkbox("Manter conectado")
            if st.form_submit_button("Entrar"):
                valid = df_usuarios[(df_usuarios['USUARIO'] == u) & (df_usuarios['SENHA'].astype(str) == p)]
                if not valid.empty:
                    st.session_state.logado, st.session_state.usuario = True, u
                    if lembrar: cookies["user_marata"] = u; cookies.save()
                    st.rerun()
                else: st.error("Incorreto.")
    with t2:
        with st.form("c"):
            uc, pc = st.text_input("Novo Usuário:").upper(), st.text_input("Senha:", type="password")
            if st.form_submit_button("Cadastrar") and uc and pc:
                novo = pd.DataFrame([{"USUARIO": uc, "SENHA": pc}])
                df_u_f = pd.concat([df_usuarios, novo], ignore_index=True)
                conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_u_f)
                st.success("OK! Faça Login."); st.cache_data.clear()
    st.stop()

# --- DASHBOARD / MENU ---
user_atual = st.session_state.usuario
is_admin = user_atual == NOME_ADMIN
is_analista = user_atual == NOME_ANALISTA
is_diretoria = user_atual == NOME_DIRETORIA

with st.sidebar:
    st.markdown(f'<div class="user-card"><div class="user-card-text">👤 {user_atual}</div></div>', unsafe_allow_html=True)
    menu = st.selectbox("Menu", ["📅 Hoje", "📋 Novo", "🔍 Ver/Editar", "📊 Dashboard"])
    if st.button("Sair"):
        if "user_marata" in cookies: del cookies["user_marata"]; cookies.save()
        st.session_state.logado = False; st.rerun()

st.title(f"SCA MARATÁ - {menu}")

# --- LÓGICA DE PÁGINAS ---
if menu == "📅 Hoje":
    hoje = datetime.now(fuso_br).strftime("%d/%m/%Y")
    df_hoje = df_agenda[df_agenda['DATA'] == hoje]
    if not is_admin and not is_diretoria:
        df_hoje = df_hoje[df_hoje['SUPERVISOR'] == user_atual]
    st.dataframe(df_hoje, use_container_width=True)

elif menu == "📋 Novo":
    col_rv = 'Região de vendas'
    sups = sorted(df_base[col_rv].unique())
    sup_sel = st.selectbox("Supervisor", sups)
    clientes = df_base[df_base[col_rv] == sup_sel]
    c_sel = st.selectbox("Cliente", clientes['Nome 1'])
    data_v = st.date_input("Data")
    if st.button("Salvar"):
        novo_v = pd.DataFrame([{
            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
            "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
            "DATA": data_v.strftime("%d/%m/%Y"),
            "SUPERVISOR": sup_sel,
            "CLIENTE": c_sel,
            "STATUS": "Planejado",
            "AGENDADO POR": user_atual
        }])
        df_f = pd.concat([df_agenda, novo_v], ignore_index=True)
        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_f)
        st.success("Agendado!"); st.cache_data.clear()

elif menu == "🔍 Ver/Editar":
    df_f = df_agenda.copy()
    if not is_admin: df_f = df_f[df_f['SUPERVISOR'] == user_atual]
    
    st.download_button("Excel", converter_para_excel(df_f), "agenda.xlsx")
    
    # Editor de dados simplificado
    df_f['EDITAR'] = False
    edicao = st.data_editor(df_f, key="edit_main", hide_index=True)
    
    marcados = edicao[edicao['EDITAR'] == True]
    if not marcados.empty:
        idx = marcados.index[0]
        with st.form("edit_form"):
            novo_status = st.selectbox("Status", ["Planejado", "Realizado", "Reagendado"])
            if st.form_submit_button("Atualizar"):
                df_agenda.at[idx, 'STATUS'] = novo_status
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                st.success("Salvo!"); st.cache_data.clear(); st.rerun()

elif menu == "📊 Dashboard":
    st.subheader("Engajamento")
    # Resumo simples
    total = len(df_base)
    agendados = df_agenda['CLIENTE'].nunique()
    c1, c2 = st.columns(2)
    c1.metric("Clientes na Base", total)
    c2.metric("Clientes Agendados", agendados)
