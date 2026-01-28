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

# --- CONFIGURAÇÃO DE COOKIES ---
cookies = EncryptedCookieManager(password="marata_secret_key_2026")
if not cookies.ready():
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# --- ESTILIZAÇÃO ---
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

# --- CONEXÃO ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

NOME_ADMIN = "LYCIO"
NOME_ANALISTA = "BARBARA"
NOME_DIRETORIA = "ALDO"

# --- FUNÇÕES DE EXPORTAÇÃO ---
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
    pdf.cell(0, 8, f"Relatorio Marata - {datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 7)
    cols = df_pdf.columns.tolist()
    for col in cols:
        pdf.cell(30, 6, str(col)[:15], border=1)
    pdf.ln()
    pdf.set_font("Arial", '', 6)
    for _, row in df_pdf.iterrows():
        for item in row:
            pdf.cell(30, 5, str(item)[:20].encode('latin-1', 'replace').decode('latin-1'), border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        df_u.columns = [str(c).strip().upper() for c in df_u.columns]
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_j.columns = [str(c).strip() for c in df_j.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
        if 'REAGENDADO PARA' not in df_a.columns: df_a['REAGENDADO PARA'] = "-"
        if 'MOTIVO REAGENDAMENTO' not in df_a.columns: df_a['MOTIVO REAGENDAMENTO'] = "-"
        df_a['LINHA'] = df_a.index + 2
        return df_b, df_j, df_a, df_u
    except:
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
    u_login = st.text_input("Usuário:").strip().upper()
    p_login = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u_login) & (df_usuarios['SENHA'].astype(str) == p_login)]
        if not valid.empty:
            st.session_state.logado, st.session_state.usuario = True, u_login
            cookies["user_marata"] = u_login
            cookies.save()
            st.rerun()
    st.stop()

# --- PERFIL E SIDEBAR ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

with st.sidebar:
    st.markdown(f'<div class="user-card"><div class="user-card-text">👤 {user_atual}</div></div>', unsafe_allow_html=True)
    opcoes_menu = ["📅 Agendamentos do Dia", "📋 Novo Agendamento", "🔍 Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria: opcoes_menu.append("📊 Dashboard de Controle")
    menu = st.selectbox("Menu Principal", opcoes_menu)
    if st.button("Sair"):
        if "user_marata" in cookies: del cookies["user_marata"]
        cookies.save()
        st.session_state.logado = False
        st.rerun()

# --- LÓGICA DE PÁGINAS ---

if menu == "📅 Agendamentos do Dia":
    st.header("📅 Agendamentos do Dia")
    hoje_str = datetime.now(fuso_br).strftime("%d/%m/%Y")
    df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
    if not (is_admin or is_diretoria):
        df_dia = df_dia[df_dia['SUPERVISOR'] == user_atual] if not is_analista else df_dia[df_dia['ANALISTA'] == user_atual]

    if not df_dia.empty:
        df_dia["EDITAR"] = False
        cols_v = ['EDITAR', 'DATA', 'CLIENTE', 'STATUS', 'REAGENDADO PARA', 'JUSTIFICATIVA']
        edicao_dia = st.data_editor(df_dia[cols_v], key="edit_dia", hide_index=True, use_container_width=True, 
                                    column_config={"EDITAR": st.column_config.CheckboxColumn("📝")}, disabled=[c for c in cols_v if c != "EDITAR"])
        
        marcados = edicao_dia[edicao_dia["EDITAR"] == True]
        if not marcados.empty:
            sel_row = df_dia.iloc[marcados.index[0]]
            st.subheader(f"Atualizar: {sel_row['CLIENTE']}")
            col1, col2, col3 = st.columns(3)
            with col1: n_st = st.selectbox("Novo Status:", ["Planejado", "Realizado", "Reagendado"], index=0)
            with col2:
                n_data_reag = st.date_input("Nova Data (se Reagendado):", datetime.now(fuso_br)) if n_st == "Reagendado" else None
            with col3:
                n_motivo = st.text_input("Motivo do Reagendamento:") if n_st == "Reagendado" else ""
            
            n_ju = st.selectbox("Justificativa Padrão:", list(df_just.iloc[:,0].dropna().unique()) + ["OUTRO"])

            if st.button("💾 ATUALIZAR STATUS"):
                idx = df_agenda[df_agenda['ID'] == sel_row['ID']].index
                df_agenda.loc[idx, 'STATUS'] = n_st
                df_agenda.loc[idx, 'JUSTIFICATIVA'] = n_ju
                if n_st == "Reagendado":
                    df_agenda.loc[idx, 'REAGENDADO PARA'] = n_data_reag.strftime("%d/%m/%Y")
                    df_agenda.loc[idx, 'MOTIVO REAGENDAMENTO'] = n_motivo
                
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                st.cache_data.clear()
                st.success("Atualizado!")
                time.sleep(1)
                st.rerun()

elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    # (Mantida estrutura original de seleção de cliente e salvamento)
    sups = sorted(df_base['Região de vendas'].unique()) if is_admin else [user_atual]
    sup_sel = st.selectbox("Supervisor:", sups)
    clientes_f = df_base[df_base['Região de vendas'] == sup_sel]
    lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
    cliente_sel = st.selectbox("Cliente:", ["Selecione..."] + lista_c)
    
    if cliente_sel != "Selecione...":
        d_visita = st.date_input("Data da Visita:", datetime.now(fuso_br))
        if st.button("💾 SALVAR"):
            cod_c, nom_c = cliente_sel.split(" - ", 1)
            nova_linha = {
                "ID": datetime.now(fuso_br).strftime("%Y%m%d%H%M%S"),
                "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
                "DATA": d_visita.strftime("%d/%m/%Y"),
                "ANALISTA": "-", "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, 
                "CLIENTE": nom_c, "JUSTIFICATIVA": "-", "STATUS": "Planejado", 
                "AGENDADO POR": user_atual, "REAGENDADO PARA": "-", "MOTIVO REAGENDAMENTO": "-"
            }
            df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame([nova_linha])], ignore_index=True)
            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
            st.cache_data.clear()
            st.success("Salvo!")
            st.rerun()

elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    df_f = df_agenda.copy() if is_admin else df_agenda[df_agenda['SUPERVISOR'] == user_atual]
    
    df_f["EDITAR"] = False
    cols_display = ['EDITAR', 'REGISTRO', 'DATA', 'CLIENTE', 'STATUS', 'REAGENDADO PARA', 'MOTIVO REAGENDAMENTO', 'JUSTIFICATIVA']
    
    edicao = st.data_editor(df_f[cols_display], key="edit_v_geral", hide_index=True, use_container_width=True,
                            column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                            disabled=[c for c in cols_display if c != "EDITAR"])
    
    marcados = edicao[edicao["EDITAR"] == True]
    if not marcados.empty:
        sel_row = df_f.iloc[marcados.index[0]]
        if st.button("🗑️ EXCLUIR AGENDAMENTO"):
            df_rest = df_agenda[df_agenda['ID'] != sel_row['ID']].drop(columns=['LINHA'], errors='ignore')
            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
            st.cache_data.clear()
            st.rerun()

elif menu == "📊 Dashboard de Controle":
    st.header("📊 Dashboard")
    st.dataframe(df_agenda[['SUPERVISOR', 'CLIENTE', 'DATA', 'STATUS', 'REAGENDADO PARA']], use_container_width=True)
