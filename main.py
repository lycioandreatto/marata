import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import io
from fpdf import FPDF
import pytz
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# --- CONEXÃO E CONFIGURAÇÕES ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

# Administrador e Analista Especial
NOME_ADMIN = "LYCIO"
NOME_ANALISTA = "BARBARA"
NOME_DIRETORIA = "ALDO"

# --- FUNÇÕES DE EXPORTAÇÃO ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio_Geral')
    return output.getvalue()

def gerar_pdf_dashboard(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, f"Relatorio Geral de Engajamento - {data_geracao}", ln=True, align='C')
    pdf.ln(5)
    
    larguras = [40, 30, 100, 40, 60] 
    pdf.set_font("Arial", 'B', 8)
    cols = ["SUPERVISOR", "CODIGO", "CLIENTE", "CIDADE/LOCAL", "STATUS AGENDA"]
    
    for i, col in enumerate(cols):
        pdf.cell(larguras[i], 8, col, border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 7)
    for _, row in df.iterrows():
        pdf.cell(larguras[0], 7, str(row['SUPERVISOR'])[:25], border=1)
        pdf.cell(larguras[1], 7, str(row['CÓDIGO']), border=1)
        pdf.cell(larguras[2], 7, str(row['NOME'])[:60], border=1)
        pdf.cell(larguras[3], 7, str(row['CIDADE'])[:25], border=1)
        pdf.cell(larguras[4], 7, str(row['STATUS AGENDA']), border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

def gerar_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, f"Agenda Marata - Gerado em {data_geracao}", ln=True, align='C')
    pdf.ln(5)
    larguras = [35, 22, 35, 70, 46, 30, 30] 
    pdf.set_font("Arial", 'B', 8)
    for i, col in enumerate(df.columns):
        if i < len(larguras):
            pdf.cell(larguras[i], 8, str(col), border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 8)
    for index, row in df.iterrows():
        for i, item in enumerate(row):
            if i < len(larguras):
                pdf.cell(larguras[i], 8, str(item)[:40], border=1)
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
        df_a['LINHA'] = df_a.index + 2
        
        for df in [df_b, df_a]:
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
                df[col] = df[col].replace('0', '')
        
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except Exception: 
        return None, None, None, pd.DataFrame(columns=["USUARIO", "SENHA"])

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- SISTEMA DE ACESSO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""

if not st.session_state.logado:
    st.title("☕ Acesso Gestão Maratá")
    tab_login, tab_cadastro = st.tabs(["Login", "Novo Cadastro"])

    with tab_login:
        with st.form("login_form"):
            u_login = st.text_input("Usuário:").strip().upper()
            p_login = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar"):
                if "USUARIO" in df_usuarios.columns and "SENHA" in df_usuarios.columns:
                    valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u_login) & (df_usuarios['SENHA'].astype(str) == p_login)]
                    if not valid.empty:
                        st.session_state.logado = True
                        st.session_state.usuario = u_login
                        st.rerun()
                    else: st.error("Usuário ou Senha incorretos.")
                else: st.error("Erro na base de usuários.")

    with tab_cadastro:
        with st.form("cad_form"):
            u_cad = st.text_input("Usuário:").strip().upper()
            p_cad = st.text_input("Senha:", type="password")
            p_cad_conf = st.text_input("Confirme Senha:", type="password")
            if st.form_submit_button("Cadastrar"):
                if u_cad and p_cad == p_cad_conf:
                    novo = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                    df_u_novo = pd.concat([df_usuarios, novo], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_u_novo)
                    st.success("Cadastrado!")
                    st.cache_data.clear()
    st.stop()

# --- PERFIL ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

# --- BARRA LATERAL ---
with st.sidebar:
    try: st.image("pngmarata.png", width=150)
    except: st.warning("Logo não encontrada.")
    st.write(f"👤 {user_atual}")
    opcoes_menu = ["Novo Agendamento", "Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria:
        opcoes_menu.append("📊 Dashboard de Controle")
    menu = st.selectbox("Menu", opcoes_menu)
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# --- DASHBOARD ---
if menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento")
    if df_base is not None and df_agenda is not None:
        # MAPEAR COLUNAS DINAMICAMENTE
        col_rv = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_cli = next((c for c in df_base.columns if c.upper() == 'CLIENTE'), 'Cliente')
        col_nom = next((c for c in df_base.columns if c.upper() == 'NOME 1'), 'Nome 1')
        col_loc = next((c for c in df_base.columns if c.upper() in ['LOCAL', 'CIDADE']), 'Local')
        
        # Resumo
        resumo_b = df_base.groupby(col_rv).size().reset_index(name='Base')
        resumo_a = df_agenda.groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Agendados')
        df_dash = pd.merge(resumo_b, resumo_a, left_on=col_rv, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Faltando'] = df_dash['Base'] - df_dash['Agendados']
        
        st.dataframe(df_dash[[col_rv, 'Base', 'Agendados', 'Faltando']], use_container_width=True, hide_index=True)

        # SEÇÃO DE EXTRAÇÃO
        st.markdown("---")
        st.subheader("📥 Extrair Relatório de Clientes")
        
        agendados_set = set(df_agenda['CÓDIGO CLIENTE'].unique())
        df_ext = df_base[[col_rv, col_cli, col_nom, col_loc]].copy()
        df_ext.columns = ['SUPERVISOR', 'CÓDIGO', 'NOME', 'CIDADE']
        df_ext['STATUS AGENDA'] = df_ext['CÓDIGO'].apply(lambda x: "Agendado" if str(x) in agendados_set else "Pendente")
        
        c1, c2 = st.columns(2)
        c1.download_button("📄 PDF", data=gerar_pdf_dashboard(df_ext), file_name="Relatorio.pdf")
        c2.download_button("📥 Excel", data=converter_para_excel(df_ext), file_name="Relatorio.xlsx")

# --- NOVO AGENDAMENTO ---
elif menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    col_rv = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
    
    if is_admin or is_diretoria:
        sups = sorted(df_base[col_rv].unique())
        sup_sel = st.selectbox("Supervisor:", ["Selecione..."] + sups)
    else:
        sup_sel = user_atual

    if sup_sel != "Selecione...":
        clientes_f = df_base[df_base[col_rv] == sup_sel]
        agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
        pendentes = clientes_f[~clientes_f['Cliente'].isin(agendados)]
        
        lista_c = sorted(pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        if lista_c:
            sel_c = st.selectbox("Cliente:", ["Selecione..."] + lista_c)
            if sel_c != "Selecione...":
                with st.form("f_add"):
                    dt = st.date_input("Data:")
                    if st.form_submit_button("Salvar"):
                        cod, nom = sel_c.split(" - ", 1)
                        novo = pd.DataFrame([{
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
                            "DATA": dt.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_sel,
                            "CÓDIGO CLIENTE": cod,
                            "CLIENTE": nom,
                            "STATUS": "Planejado (X)",
                            "JUSTIFICATIVA": "-"
                        }])
                        df_ag_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), novo], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_ag_final)
                        st.success("Salvo!")
                        st.cache_data.clear()
                        st.rerun()
        else: st.success("Tudo agendado!")

# --- VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual] if not is_admin else df_agenda
    if not df_f.empty:
        df_f["EDITAR"] = False
        edicao = st.data_editor(df_f, key="ed_v1", hide_index=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")})
        
        marcados = edicao[edicao["EDITAR"] == True]
        if not marcados.empty:
            sel = marcados.iloc[0]
            with st.form("ed_f"):
                n_st = st.selectbox("Status:", ["Planejado (X)", "Realizado", "Reagendado"], index=0)
                n_ju = st.text_input("Obs:")
                if st.form_submit_button("Atualizar"):
                    df_agenda.loc[df_agenda['ID'] == sel['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
