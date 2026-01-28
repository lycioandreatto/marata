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

# Administrador e Analistas
NOME_ADMIN = "LYCIO"
NOME_ANALISTA = "BARBARA"
NOME_DIRETORIA = "ALDO"

# --- FUNÇÕES DE EXPORTAÇÃO (COM CORREÇÃO UNICODE) ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def limpar_texto(txt):
    """Remove caracteres que quebram o PDF latin-1 (como emojis)"""
    if not txt: return ""
    return str(txt).encode('latin-1', 'ignore').decode('latin-1')

def gerar_pdf_dashboard(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, limpar_texto(f"Relatório de Engajamento - {data_geracao}"), ln=True, align='C')
    pdf.ln(5)
    
    larguras = [40, 30, 100, 40, 60] 
    pdf.set_font("Arial", 'B', 8)
    cols = ["SUPERVISOR", "CODIGO", "CLIENTE", "LOCALIDADE", "STATUS"]
    for i, col in enumerate(cols):
        pdf.cell(larguras[i], 8, col, border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 7)
    for _, row in df.iterrows():
        sup = limpar_texto(row.iloc[0])[:25]
        cod = limpar_texto(row.iloc[1])
        cli = limpar_texto(row.iloc[2])[:60]
        loc = limpar_texto(row.iloc[3])[:25]
        # Converte o emoji visual para texto no PDF
        status_raw = str(row.iloc[4])
        status_txt = "Agendado" if "Agendado" in status_raw else "Pendente"
        
        pdf.cell(larguras[0], 7, sup, border=1)
        pdf.cell(larguras[1], 7, cod, border=1)
        pdf.cell(larguras[2], 7, cli, border=1)
        pdf.cell(larguras[3], 7, loc, border=1)
        pdf.cell(larguras[4], 7, status_txt, border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

def gerar_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, limpar_texto(f"Agenda Maratá - Gerado em {data_geracao}"), ln=True, align='C')
    pdf.ln(5)
    
    larguras = [35, 22, 35, 70, 46, 30, 30] 
    pdf.set_font("Arial", 'B', 8)
    for i, col in enumerate(df.columns[:7]):
        pdf.cell(larguras[i], 8, limpar_texto(str(col)), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    for _, row in df.iterrows():
        for i in range(len(larguras)):
            pdf.cell(larguras[i], 8, limpar_texto(str(row.iloc[i]))[:40], border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        df_u.columns = [str(c).strip().upper() for c in df_u.columns]
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
            
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
        df_a['LINHA'] = df_a.index + 2
        
        # Padronização de códigos de cliente
        for df in [df_b, df_a]:
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
                df[col] = df[col].replace('0', '')
        
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_a, df_u
    except Exception: 
        return None, None, pd.DataFrame(columns=["USUARIO", "SENHA"])

df_base, df_agenda, df_usuarios = carregar_dados()

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
                if "USUARIO" in df_usuarios.columns:
                    valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u_login) & (df_usuarios['SENHA'].astype(str) == p_login)]
                    if not valid.empty:
                        st.session_state.logado = True
                        st.session_state.usuario = u_login
                        st.rerun()
                    else: st.error("Usuário ou Senha incorretos.")
    
    with tab_cadastro:
        with st.form("cad_form"):
            u_cad = st.text_input("Novo Usuário:").strip().upper()
            p_cad = st.text_input("Senha:", type="password")
            if st.form_submit_button("Cadastrar"):
                if u_cad and p_cad:
                    novo_u = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                    conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=pd.concat([df_usuarios, novo_u]))
                    st.success("Cadastrado! Faça login.")
    st.stop()

# --- VARIÁVEIS DE PERMISSÃO ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

# --- INTERFACE ---
with st.sidebar:
    st.markdown(f"👤 **{user_atual}**")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Minha Agenda", "📊 Dashboard"])
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# --- LÓGICA DE PÁGINAS ---

if menu == "Novo Agendamento":
    st.header("📋 Novo Agendamento")
    if df_base is not None:
        # Lógica de seleção de supervisor
        col_rv = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        if is_admin or is_analista or is_diretoria:
            sups = sorted(df_base[col_rv].unique())
            sup_sel = st.selectbox("Filtrar por Supervisor:", ["Selecione..."] + sups)
        else:
            sup_sel = user_atual

        if sup_sel != "Selecione...":
            # Filtra clientes pendentes
            cli_da_base = df_base[df_base[col_rv] == sup_sel]
            já_agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
            pendentes = cli_da_base[~cli_da_base['Cliente'].isin(já_agendados)]
            
            lista_display = sorted(pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            
            if not lista_display:
                st.success("✅ Todos os clientes da sua base já foram agendados!")
            else:
                cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_display)
                
                if cliente_sel != "Selecione...":
                    with st.form("form_multi_datas"):
                        st.info("Você pode agendar até 4 datas diferentes para este cliente.")
                        c1, c2 = st.columns(2)
                        with c1:
                            d1 = st.date_input("Data 1", datetime.now(fuso_br))
                            d2 = st.date_input("Data 2 (Opcional)", value=None)
                        with c2:
                            d3 = st.date_input("Data 3 (Opcional)", value=None)
                            d4 = st.date_input("Data 4 (Opcional)", value=None)
                        
                        if st.form_submit_button("Confirmar Agendamento(s)"):
                            cod, nom = cliente_sel.split(" - ", 1)
                            novos_registros = []
                            datas_escolhidas = [d for d in [d1, d2, d3, d4] if d is not None]
                            
                            for dt in datas_escolhidas:
                                novos_registros.append({
                                    "ID": datetime.now().strftime("%Y%m%d%H%M%S") + str(time.time())[-4:],
                                    "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
                                    "DATA": dt.strftime("%d/%m/%Y"),
                                    "SUPERVISOR": sup_sel,
                                    "CÓDIGO CLIENTE": cod,
                                    "CLIENTE": nom,
                                    "STATUS": "Planejado (X)",
                                    "JUSTIFICATIVA": "-"
                                })
                            
                            df_novo = pd.DataFrame(novos_registros)
                            df_atualizado = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), df_novo], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_atualizado)
                            st.cache_data.clear()
                            st.success(f"✅ {len(datas_escolhidas)} visita(s) agendada(s)!")
                            time.sleep(1)
                            st.rerun()

elif menu == "Minha Agenda":
    st.header("🔍 Gerenciar Visitas")
    df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual] if not (is_admin or is_diretoria) else df_agenda
    
    col_btn1, col_btn2, _ = st.columns([1,1,2])
    with col_btn1: st.download_button("📥 Excel", data=converter_para_excel(df_f), file_name="agenda.xlsx")
    with col_btn2: st.download_button("📄 PDF", data=gerar_pdf(df_f), file_name="agenda.pdf")
    
    st.data_editor(df_f, hide_index=True)

elif menu == "📊 Dashboard":
    st.header("📊 Engajamento")
    if df_base is not None and df_agenda is not None:
        col_rv = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        
        # Cálculo de progresso
        resumo_base = df_base.groupby(col_rv).size().reset_index(name='Total')
        resumo_ag = df_agenda.groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Agendados')
        
        dash = pd.merge(resumo_base, resumo_ag, left_on=col_rv, right_on='SUPERVISOR', how='left').fillna(0)
        dash['Progresso'] = (dash['Agendados'] / dash['Total'] * 100).round(1).astype(str) + '%'
        
        st.table(dash[[col_rv, 'Total', 'Agendados', 'Progresso']])
        
        # Exportação Detalhada
        st.markdown("---")
        df_detalhe = df_base[[col_rv, 'Cliente', 'Nome 1', 'Local']].copy()
        ag_set = set(df_agenda['CÓDIGO CLIENTE'].unique())
        df_detalhe['STATUS'] = df_detalhe['Cliente'].apply(lambda x: "✅ Agendado" if str(x) in ag_set else "❌ Pendente")
        
        st.download_button("📄 Exportar PDF Detalhado (Sem Erros)", 
                           data=gerar_pdf_dashboard(df_detalhe), 
                           file_name="Relatorio_Engajamento.pdf")
