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

NOME_ADMIN = "LYCIO"
NOME_ANALISTA = "BARBARA"
NOME_DIRETORIA = "ALDO"

# --- FUNÇÕES DE EXPORTAÇÃO ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def limpar_texto(txt):
    """Remove caracteres que quebram o PDF padrão latin-1"""
    if not txt: return ""
    return str(txt).encode('latin-1', 'ignore').decode('latin-1')

def gerar_pdf(df, titulo="Relatorio"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, limpar_texto(f"{titulo} - {data_geracao}"), ln=True, align='C')
    pdf.ln(5)
    
    # Ajuste dinâmico de larguras baseado no número de colunas (máximo 7 para não quebrar)
    pdf.set_font("Arial", 'B', 8)
    cols = df.columns.tolist()
    largura_celula = 270 / len(cols) if len(cols) > 0 else 30
    
    for col in cols:
        pdf.cell(largura_celula, 8, limpar_texto(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 7)
    for _, row in df.iterrows():
        for item in row:
            pdf.cell(largura_celula, 7, limpar_texto(item)[:40], border=1)
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
        df_a.columns = [str(c).strip() for c in df_a.columns]
            
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
        df_a['LINHA'] = df_a.index + 2
        
        for df in [df_b, df_a]:
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str).replace('0', '')
        
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
    t_login, t_cad = st.tabs(["Login", "Novo Cadastro"])
    with t_login:
        with st.form("l"):
            u = st.text_input("Usuário:").strip().upper()
            p = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar"):
                valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u) & (df_usuarios['SENHA'].astype(str) == p)]
                if not valid.empty:
                    st.session_state.logado = True
                    st.session_state.usuario = u
                    st.rerun()
                else: st.error("Erro de login.")
    st.stop()

# --- PERFIL ---
user_atual = st.session_state.usuario
is_admin = user_atual == NOME_ADMIN
is_analista = user_atual == NOME_ANALISTA
is_diretoria = user_atual == NOME_DIRETORIA

# --- MENU LATERAL ---
with st.sidebar:
    st.write(f"👤 **{user_atual}**")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda", "📊 Dashboard de Controle"])
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# --- DASHBOARD ---
if menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento")
    if df_base is not None and df_agenda is not None:
        col_rv = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        resumo_base = df_base.groupby(col_rv).size().reset_index(name='Total na Base')
        resumo_ag = df_agenda.groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Agendados')
        
        df_dash = pd.merge(resumo_base, resumo_ag, left_on=col_rv, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Progresso'] = (df_dash['Agendados'] / df_dash['Total na Base'] * 100).round(1).astype(str) + '%'
        
        st.dataframe(df_dash, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📥 Exportar Relatório de Engajamento")
        col_e1, col_e2, _ = st.columns([1,1,2])
        # Criando DF limpo para exportação
        df_exp_dash = df_dash.copy()
        with col_e1:
            st.download_button("📄 PDF Dashboard", data=gerar_pdf(df_exp_dash, "Engajamento"), file_name="Dash_Engajamento.pdf")
        with col_e2:
            st.download_button("📥 Excel Dashboard", data=converter_para_excel(df_exp_dash), file_name="Dash_Engajamento.xlsx")

# --- NOVO AGENDAMENTO ---
elif menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    col_rv = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
    
    if is_admin or is_diretoria or is_analista:
        sups = sorted(df_base[col_rv].unique())
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
    else: sup_sel = user_atual

    if sup_sel != "Selecione...":
        clientes_sup = df_base[df_base[col_rv] == sup_sel]
        agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
        pendentes = clientes_sup[~clientes_sup['Cliente'].isin(agendados)]
        
        lista_c = sorted(pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        
        if not lista_c: st.success("✅ Tudo agendado!")
        else:
            cliente_sel = st.selectbox("Cliente:", ["Selecione..."] + lista_c)
            if cliente_sel != "Selecione...":
                qtd = st.number_input("Quantas visitas para este cliente?", 1, 4, 1)
                with st.form("f_novo"):
                    cols_d = st.columns(qtd)
                    datas_f = []
                    for i in range(qtd):
                        datas_f.append(cols_d[i].date_input(f"Data {i+1}", datetime.now(fuso_br), key=f"dt_{i}"))
                    
                    if st.form_submit_button("Salvar Agendamentos"):
                        cod, nom = cliente_sel.split(" - ", 1)
                        novos = []
                        for d in datas_f:
                            novos.append({
                                "ID": datetime.now().strftime("%Y%m%d%H%M%S") + str(time.time())[-2:],
                                "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
                                "DATA": d.strftime("%d/%m/%Y"),
                                "SUPERVISOR": sup_sel,
                                "CÓDIGO CLIENTE": cod,
                                "CLIENTE": nom,
                                "STATUS": "Planejado (X)",
                                "JUSTIFICATIVA": "-"
                            })
                        df_up = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novos)], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_up)
                        st.cache_data.clear()
                        st.success("Salvo com sucesso!")
                        time.sleep(1)
                        st.rerun()

# --- VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual] if not (is_admin or is_analista) else df_agenda
    
    if not df_f.empty:
        col_v1, col_v2, _ = st.columns([1,1,2])
        # Selecionando colunas essenciais para o PDF não estourar a largura
        cols_export = ['DATA', 'SUPERVISOR', 'CLIENTE', 'STATUS', 'JUSTIFICATIVA']
        with col_v1:
            st.download_button("📄 PDF Agenda", data=gerar_pdf(df_f[cols_export], "Minha_Agenda"), file_name="Minha_Agenda.pdf")
        with col_v2:
            st.download_button("📥 Excel Agenda", data=converter_para_excel(df_f), file_name="Minha_Agenda.xlsx")
        
        df_f['EDITAR'] = False
        edicao = st.data_editor(df_f, hide_index=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")})
        
        selecionado = edicao[edicao['EDITAR'] == True]
        if not selecionado.empty:
            sel = selecionado.iloc[0]
            with st.form("edit_f"):
                st.write(f"Editando: {sel['CLIENTE']}")
                n_status = st.selectbox("Status", ["Planejado (X)", "Realizado", "Reagendado"], index=0)
                n_just = st.text_input("Justificativa/Obs", value=sel['JUSTIFICATIVA'])
                if st.form_submit_button("Atualizar"):
                    df_agenda.loc[df_agenda['ID'] == sel['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_status, n_just]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
