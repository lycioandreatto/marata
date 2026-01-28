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

# --- ESTILIZAÇÃO DOS CARDS E PERFIL ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #d3d3d3;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    [data-testid="stMetric"] label, 
    [data-testid="stMetric"] div {
        color: black !important;
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
    .user-card-text {
        color: white;
        font-weight: bold;
        font-size: 1.1em;
        letter-spacing: 0.5px;
    }
    .user-card-icon {
        font-size: 1.5em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO E CONFIGURAÇÕES ---
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
    if tipo_relatorio == "AGENDA" and "REGISTRO" in df_pdf.columns:
        try:
            df_pdf['REGISTRO_DT'] = pd.to_datetime(df_pdf['REGISTRO'], dayfirst=True)
            df_pdf = df_pdf.sort_values(by='REGISTRO_DT', ascending=False).drop(columns=['REGISTRO_DT'])
        except:
            df_pdf = df_pdf.sort_values(by='REGISTRO', ascending=False)
    
    pdf.set_font("Arial", 'B', 12)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 8, f"Relatorio Marata - Gerado em {data_geracao}", ln=True, align='C')
    pdf.ln(3)
    
    cols = df_pdf.columns.tolist()
    largura_total = 275
    qtd_cols = len(cols)
    if qtd_cols > 8:
        tamanho_fonte_cabecalho, tamanho_fonte_dados, limite_texto = 5, 4, 25
    elif qtd_cols > 6:
        tamanho_fonte_cabecalho, tamanho_fonte_dados, limite_texto = 6, 5, 30
    else:
        tamanho_fonte_cabecalho, tamanho_fonte_dados, limite_texto = 8, 7, 40

    largura_cliente, largura_supervisor, largura_agendado, largura_data = 60, 30, 30, 18
    largura_justificativa, largura_registro, largura_cidade = 50, 25, 40
    
    pdf.set_font("Arial", 'B', tamanho_fonte_cabecalho)
    for col in cols:
        c_up = str(col).upper()
        if c_up == "CLIENTE": w = largura_cliente
        elif c_up == "SUPERVISOR": w = largura_supervisor
        elif c_up == "AGENDADO POR": w = largura_agendado
        elif c_up == "DATA": w = largura_data
        elif c_up == "JUSTIFICATIVA": w = largura_justificativa
        elif c_up == "REGISTRO": w = largura_registro
        elif c_up == "CIDADE": w = largura_cidade
        else: w = (largura_total - 253) / (len(cols)-7) if len(cols) > 7 else 30
        pdf.cell(w, 6, str(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', tamanho_fonte_dados) 
    for _, row in df_pdf.iterrows():
        for i, item in enumerate(row):
            texto = str(item)[:limite_texto].encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(30, 5, texto, border=1) # Simplificado para garantir fluxo
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
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
        if 'AGENDADO POR' not in df_a.columns: df_a['AGENDADO POR'] = "-"
        df_a['LINHA'] = df_a.index + 2
        for df in [df_b, df_a]:
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str).replace('0', '')
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except:
        return None, None, None, pd.DataFrame(columns=["USUARIO", "SENHA"])

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- SISTEMA DE ACESSO ---
if "logado" not in st.session_state:
    if "user_marata" in cookies:
        st.session_state.logado, st.session_state.usuario = True, cookies["user_marata"]
    else:
        st.session_state.logado, st.session_state.usuario = False, ""

if not st.session_state.logado:
    st.title("☕ Acesso Gestão Maratá")
    tab_login, tab_cadastro = st.tabs(["Login", "Novo Cadastro"])
    with tab_login:
        with st.form("login_form"):
            u_login = st.text_input("Usuário:").strip().upper()
            p_login = st.text_input("Senha:", type="password")
            lembrar = st.checkbox("Manter conectado")
            if st.form_submit_button("Entrar"):
                valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u_login) & (df_usuarios['SENHA'].astype(str) == p_login)]
                if not valid.empty:
                    st.session_state.logado, st.session_state.usuario = True, u_login
                    if lembrar: cookies["user_marata"] = u_login; cookies.save()
                    st.rerun()
                else: st.error("Dados incorretos.")
    with tab_cadastro:
        with st.form("cad_form"):
            u_cad, p_cad, p_cad_conf = st.text_input("Usuário:").strip().upper(), st.text_input("Senha:", type="password"), st.text_input("Confirme:", type="password")
            if st.form_submit_button("Cadastrar"):
                if p_cad == p_cad_conf and u_cad:
                    novo_u = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                    conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=pd.concat([df_usuarios, novo_u], ignore_index=True))
                    st.success("Cadastrado!"); st.cache_data.clear()
    st.stop()

# --- PERFIL ---
user_atual = st.session_state.usuario
is_admin, is_analista, is_diretoria = (user_atual == NOME_ADMIN), (user_atual == NOME_ANALISTA), (user_atual == NOME_DIRETORIA)
label_display = "ADMINISTRADOR" if is_admin else f"DIRETORIA {user_atual}" if is_diretoria else f"ANALISTA {user_atual}" if is_analista else f"SUPERVISOR {user_atual}"
user_icon = "👑" if is_admin else "📈" if is_diretoria else "🔬" if is_analista else "👤"
border_color = "#FFD700" if is_admin else "#1E90FF" if is_diretoria else "#9370DB" if is_analista else "#ff4b4b"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f'<div class="user-card" style="border-left: 5px solid {border_color};"><div class="user-card-icon">{user_icon}</div><div class="user-card-text">{label_display}</div></div>', unsafe_allow_html=True)
    opcoes_menu = ["📅 Agendamentos do Dia", "📋 Novo Agendamento", "🔍 Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria: opcoes_menu.append("📊 Dashboard de Controle")
    menu = st.selectbox("Menu Principal", opcoes_menu)
    if st.button("Sair"):
        if "user_marata" in cookies: del cookies["user_marata"]; cookies.save()
        st.session_state.logado = False; st.rerun()

st.markdown("<h4 style='text-align: center; color: white; margin-top: -50px;'>SISTEMA DE CONTROLE DE AGENDAMENTOS (SCA) - MARATÁ</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- LÓGICA DE PÁGINAS ---
if menu == "📅 Agendamentos do Dia":
    st.header("📅 Agendamentos do Dia")
    hoje_str = datetime.now(fuso_br).strftime("%d/%m/%Y")
    if df_agenda is not None and not df_agenda.empty:
        df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
        if not (is_admin or is_diretoria):
            df_dia = df_dia[df_dia['ANALISTA' if is_analista else 'SUPERVISOR'] == user_atual]
        st.metric("Visitas Hoje", len(df_dia))
        if not df_dia.empty:
            df_dia["EDITAR"] = False
            edicao_dia = st.data_editor(df_dia[['EDITAR', 'DATA', 'SUPERVISOR', 'CLIENTE', 'STATUS']], key="ed_dia", hide_index=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")})
            if edicao_dia["EDITAR"].any():
                st.info("Use a aba 'Ver/Editar' para alterações detalhadas.")
        else: st.info("Sem visitas para hoje.")

elif menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento")
    if df_base is not None and df_agenda is not None:
        col_rv = next((c for c in df_base.columns if 'REGIÃO' in c.upper()), 'Região de vendas')
        col_ana = next((c for c in df_base.columns if 'ANALISTA' in c.upper()), 'Analista')
        
        # Filtros
        f1, f2 = st.columns(2)
        with f1: 
            lista_a = sorted(df_base[col_ana].unique())
            sel_a = st.selectbox("Analista:", ["Todos"] + lista_a)
        df_f = df_base.copy() if sel_a == "Todos" else df_base[df_base[col_ana] == sel_a]
        
        # Cálculos Dashboard
        res_b = df_f.groupby(col_rv).size().reset_index(name='Total')
        res_a = df_agenda[df_agenda['SUPERVISOR'].isin(df_f[col_rv])].groupby('SUPERVISOR').size().reset_index(name='Agendados')
        df_dash = pd.merge(res_b, res_a, left_on=col_rv, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['%'] = (df_dash['Agendados'] / df_dash['Total'] * 100).round(1)
        
        st.dataframe(df_dash, use_container_width=True)

        # RANKING
        st.markdown("---")
        st.subheader("🏆 Ranking de Engajamento")
        df_rank = df_dash.sort_values('%', ascending=False).reset_index(drop=True)
        df_rank.index += 1
        def medal(p): return "🥇" if p==1 else "🥈" if p==2 else "🥉" if p==3 else f"{p}º"
        df_rank['POS'] = [medal(i) for i in df_rank.index]
        st.table(df_rank[['POS', col_rv, 'Agendados', '%']])

elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    if df_base is not None:
        col_rv = next((c for c in df_base.columns if 'REGIÃO' in c.upper()), 'Região de vendas')
        sup_sel = user_atual if not (is_admin or is_analista or is_diretoria) else st.selectbox("Supervisor:", sorted(df_base[col_rv].unique()))
        
        clientes = df_base[df_base[col_rv] == sup_sel]
        lista_c = sorted(clientes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        c_sel = st.selectbox("Cliente:", ["Selecione..."] + lista_c)
        
        if c_sel != "Selecione...":
            with st.form("f_novo"):
                dt = st.date_input("Data:", datetime.now(fuso_br))
                if st.form_submit_button("Salvar"):
                    cod, nom = c_sel.split(" - ", 1)
                    nova = pd.DataFrame([{"ID": datetime.now().strftime("%Y%m%d%H%M%S"), "DATA": dt.strftime("%d/%m/%Y"), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod, "CLIENTE": nom, "STATUS": "Planejado", "AGENDADO POR": user_atual}])
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova], ignore_index=True))
                    st.success("Agendado!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    if df_agenda is not None:
        df_f = df_agenda if (is_admin or is_diretoria) else df_agenda[df_agenda['SUPERVISOR'] == user_atual]
        df_f["EDITAR"] = False
        edicao = st.data_editor(df_f[["EDITAR", "REGISTRO", "DATA", "CLIENTE", "STATUS", "JUSTIFICATIVA"]], key="ed_full", hide_index=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")})
        
        marcados = edicao[edicao["EDITAR"] == True]
        if not marcados.empty:
            sel_row = df_f.iloc[marcados.index[0]]
            with st.form("form_edit_final"):
                st.subheader(f"Editar: {sel_row['CLIENTE']}")
                n_st = st.selectbox("Status:", ["Planejado", "Realizado", "Reagendado"], index=0)
                n_ju = st.text_input("Justificativa:", value=sel_row['JUSTIFICATIVA'])
                if st.form_submit_button("Atualizar"):
                    df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.success("Atualizado!"); st.cache_data.clear(); time.sleep(1); st.rerun()
