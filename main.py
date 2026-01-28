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
from streamlit_js_eval import streamlit_js_eval

# --- CONFIGURAÇÃO DE COOKIES ---
cookies = EncryptedCookieManager(password="marata_secret_key_2026")
if not cookies.ready():
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Maratá - SCA", page_icon="☕", layout="wide")

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
    [data-testid="stMetric"] label, [data-testid="stMetric"] div { color: black !important; }
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
    .user-card-text { color: white; font-weight: bold; font-size: 1.1em; letter-spacing: 0.5px; }
    .user-card-icon { font-size: 1.5em; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

NOME_ADMIN, NOME_ANALISTA, NOME_DIRETORIA = "LYCIO", "BARBARA", "ALDO"

def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def gerar_pdf(df, tipo_relatorio="GERAL"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    df_pdf = df.copy()
    if tipo_relatorio == "AGENDA" and "REGISTRO" in df_pdf.columns:
        try:
            df_pdf['REGISTRO_DT'] = pd.to_datetime(df_pdf['REGISTRO'], dayfirst=True)
            df_pdf = df_pdf.sort_values(by='REGISTRO_DT', ascending=False).drop(columns=['REGISTRO_DT'])
        except: pass
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Relatorio Marata - Gerado em {datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(3)
    cols = df_pdf.columns.tolist()
    pdf.set_font("Arial", 'B', 6)
    w_col = 275 / len(cols)
    for col in cols: pdf.cell(w_col, 6, str(col), border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 5)
    for _, row in df_pdf.iterrows():
        for item in row:
            texto = str(item)[:40].encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(w_col, 5, texto, border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        for d in [df_b, df_j, df_a, df_u]: d.columns = [str(c).strip().upper() for c in d.columns]
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
        if 'LATITUDE' not in df_a.columns: df_a['LATITUDE'] = ""
        if 'LONGITUDE' not in df_a.columns: df_a['LONGITUDE'] = ""
        df_a['LINHA'] = df_a.index + 2
        return df_b, df_j, df_a, df_u
    except: return None, None, None, pd.DataFrame(columns=["USUARIO", "SENHA"])

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

if "logado" not in st.session_state:
    if "user_marata" in cookies:
        st.session_state.logado, st.session_state.usuario = True, cookies["user_marata"]
    else: st.session_state.logado, st.session_state.usuario = False, ""

if not st.session_state.logado:
    st.markdown('<div style="display:flex;align-items:center;gap:15px;"><img src="https://raw.githubusercontent.com/lycioandreatto/marata/main/pngmarata" width="60"><h1 style="color:#ff4b4b;">Acesso Gestão Maratá</h1></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Login", "Novo Cadastro"])
    with t1:
        with st.form("l"):
            u, p, l = st.text_input("Usuário:").upper(), st.text_input("Senha:", type="password"), st.checkbox("Manter conectado")
            if st.form_submit_button("Entrar"):
                if not df_usuarios[(df_usuarios['USUARIO'] == u) & (df_usuarios['SENHA'].astype(str) == p)].empty:
                    st.session_state.logado, st.session_state.usuario = True, u
                    if l: cookies["user_marata"] = u; cookies.save()
                    st.rerun()
                else: st.error("Erro!")
    with t2:
        with st.form("c"):
            uc, pc, pcc = st.text_input("Usuário:").upper(), st.text_input("Senha:", type="password"), st.text_input("Repita:", type="password")
            if st.form_submit_button("Cadastrar") and uc and pc == pcc:
                conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=pd.concat([df_usuarios, pd.DataFrame([{"USUARIO": uc, "SENHA": pc}])]))
                st.success("OK!"); st.rerun()
    st.stop()

user_atual = st.session_state.usuario
is_admin, is_analista, is_diretoria = user_atual == NOME_ADMIN, user_atual == NOME_ANALISTA, user_atual == NOME_DIRETORIA
with st.sidebar:
    st.markdown(f'<div class="user-card"><div class="user-card-text">👤 {user_atual}</div></div>', unsafe_allow_html=True)
    menu = st.selectbox("Menu", ["📅 Agendamentos do Dia", "📋 Novo Agendamento", "🔍 Ver/Editar Minha Agenda", "📊 Dashboard de Controle"])
    if st.button("Sair"):
        if "user_marata" in cookies: del cookies["user_marata"]; cookies.save()
        st.session_state.logado = False; st.rerun()

st.markdown("<h4 style='text-align: center;'>SISTEMA MARATÁ (SCA)</h4>", unsafe_allow_html=True)

if menu == "📅 Agendamentos do Dia":
    st.header("📅 Hoje")
    hoje = datetime.now(fuso_br).strftime("%d/%m/%Y")
    df_dia = df_agenda[df_agenda['DATA'] == hoje].copy()
    if not (is_admin or is_diretoria): df_dia = df_dia[df_dia['SUPERVISOR'] == user_atual]
    
    if not df_dia.empty:
        df_dia["EDITAR"] = False
        ed = st.data_editor(df_dia[['EDITAR', 'CLIENTE', 'STATUS', 'JUSTIFICATIVA']], hide_index=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")})
        if not ed[ed["EDITAR"]].empty:
            sel = df_dia.iloc[ed[ed["EDITAR"]].index[0]]
            with st.container():
                st.subheader(f"Atualizar: {sel['CLIENTE']}")
                n_st = st.radio("Status:", ["Planejado", "Realizado", "Reagendado"], horizontal=True)
                n_ju = st.selectbox("Justificativa:", list(df_just.iloc[:,0].unique()) + ["OUTRO"])
                m_o = st.text_input("Especifique:") if n_ju == "OUTRO" else ""
                
                # --- O FIX DE IDENTAÇÃO DA LINHA 432 ---
                if st.button("💾 ATUALIZAR STATUS"):
                    with st.spinner("GPS..."):
                        loc = streamlit_js_eval(js_expressions="""new Promise((r)=>{navigator.geolocation.getCurrentPosition((p)=>{r({lat:p.coords.latitude,lon:p.coords.longitude})},(e)=>{r(null)},{timeout:5000})})""", want_output=True)
                    lat = loc.get('lat') if loc else "Erro GPS"
                    lon = loc.get('lon') if loc else "Erro GPS"
                    final_j = m_o if n_ju == "OUTRO" else n_ju
                    df_agenda.loc[df_agenda['ID'] == sel['ID'], ['STATUS', 'JUSTIFICATIVA', 'LATITUDE', 'LONGITUDE']] = [n_st, final_j, lat, lon]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()
    else: st.info("Sem visitas.")

elif menu == "📊 Dashboard de Controle":
    st.header("📊 Dashboard")
    resumo = df_agenda.groupby('SUPERVISOR').size().reset_index(name='AGENDADOS')
    st.dataframe(resumo, use_container_width=True)
    st.subheader("🏆 Ranking")
    df_rank = resumo.sort_values('AGENDADOS', ascending=False).reset_index(drop=True)
    df_rank.index += 1
    st.table(df_rank)

elif menu == "📋 Novo Agendamento":
    st.header("📋 Novo")
    c_rv = next((c for c in df_base.columns if 'REGIÃO' in c), 'REGIÃO DE VENDAS')
    sup = user_atual if not (is_admin or is_analista) else st.selectbox("Sup:", sorted(df_base[c_rv].unique()))
    cli = st.selectbox("Cliente:", sorted(df_base[df_base[c_rv]==sup].apply(lambda x: f"{x['CLIENTE']} - {x['NOME 1']}", axis=1)))
    if cli:
        with st.form("nf"):
            dt = st.date_input("Data:", datetime.now(fuso_br))
            if st.form_submit_button("Salvar"):
                cod, nom = cli.split(" - ", 1)
                nova = pd.DataFrame([{"ID": datetime.now(fuso_br).strftime("%Y%m%d%H%M%S"), "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"), "DATA": dt.strftime("%d/%m/%Y"), "SUPERVISOR": sup, "CÓDIGO CLIENTE": cod, "CLIENTE": nom, "STATUS": "Planejado", "JUSTIFICATIVA": "-"}])
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova]))
                st.cache_data.clear(); st.success("OK!"); st.rerun()

elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar")
    df_f = df_agenda if is_admin else df_agenda[df_agenda['SUPERVISOR'] == user_atual]
    st.dataframe(df_f.drop(columns=['LINHA'], errors='ignore'), use_container_width=True)
    if st.button("🗑️ LIMPAR MINHA AGENDA"):
        df_rest = df_agenda[df_agenda['SUPERVISOR'] != user_atual].drop(columns=['LINHA'], errors='ignore')
        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
        st.cache_data.clear(); st.rerun()
