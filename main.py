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
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def limpar_texto(txt):
    """Remove caracteres que quebram o PDF latin-1"""
    if not txt: return ""
    return str(txt).encode('latin-1', 'ignore').decode('latin-1')

def gerar_pdf_dashboard(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, f"Relatorio de Engajamento - {data_geracao}", ln=True, align='C')
    pdf.ln(5)
    
    larguras = [40, 30, 100, 40, 60] 
    pdf.set_font("Arial", 'B', 8)
    cols = ["SUPERVISOR", "CODIGO", "CLIENTE", "LOCALIDADE", "STATUS"]
    
    for i, col in enumerate(cols):
        pdf.cell(larguras[i], 8, col, border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 7)
    for _, row in df.iterrows():
        # Limpamos cada campo para evitar o erro de Unicode
        sup = limpar_texto(row.iloc[0])[:25]
        cod = limpar_texto(row.iloc[1])
        cli = limpar_texto(row.iloc[2])[:60]
        loc = limpar_texto(row.iloc[3])[:25]
        # Removemos o emoji para o PDF não dar erro
        status = "Agendado" if "Agendado" in str(row.iloc[4]) else "Pendente"
        
        pdf.cell(larguras[0], 7, sup, border=1)
        pdf.cell(larguras[1], 7, cod, border=1)
        pdf.cell(larguras[2], 7, cli, border=1)
        pdf.cell(larguras[3], 7, loc, border=1)
        pdf.cell(larguras[4], 7, status, border=1)
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
                pdf.cell(larguras[i], 8, limpar_texto(item)[:40], border=1)
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
                    else:
                        st.error("Usuário ou Senha incorretos.")
                else:
                    st.error("Erro na base de usuários.")

    with tab_cadastro:
        with st.form("cad_form"):
            st.write("Crie sua conta")
            u_cad = st.text_input("Nome de Usuário:").strip().upper()
            p_cad = st.text_input("Defina uma Senha:", type="password")
            p_cad_conf = st.text_input("Repita a Senha:", type="password")
            
            if st.form_submit_button("Finalizar Cadastro"):
                if u_cad and p_cad == p_cad_conf:
                    novo_user = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                    df_final_u = pd.concat([df_usuarios, novo_user], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_final_u)
                    st.success("Cadastro realizado!")
                    st.cache_data.clear()
    st.stop()

user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

if is_admin: label_display = "ADMINISTRADOR"
elif is_diretoria: label_display = f"DIRETORIA {user_atual}"
elif is_analista: label_display = f"ANALISTA {user_atual}"
else: label_display = f"SUPERVISOR {user_atual}"

# --- BARRA LATERAL ---
with st.sidebar:
    try: st.image("pngmarata.png", width=150)
    except: st.warning("Logo não encontrada.")
    st.markdown(f"👤 **{label_display}**")
    opcoes_menu = ["Novo Agendamento", "Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria:
        opcoes_menu.append("📊 Dashboard de Controle")
    menu = st.selectbox("Menu Principal", opcoes_menu)
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Limpeza em Massa")
    if df_agenda is not None and not df_agenda.empty:
        if is_admin or is_analista or is_diretoria:
            lista_sups = sorted(df_agenda['SUPERVISOR'].unique())
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups)
            if sup_limpar != "Selecione..." and st.button(f"⚠️ APAGAR TUDO: {sup_limpar}"):
                df_rest = df_agenda[df_agenda['SUPERVISOR'] != sup_limpar].drop(columns=['LINHA'], errors='ignore')
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                st.cache_data.clear()
                st.rerun()

# --- PÁGINA: DASHBOARD ---
if menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento por Supervisor")
    if df_base is not None and df_agenda is not None:
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_cli_base = next((c for c in df_base.columns if c.upper() == 'CLIENTE'), 'Cliente')
        col_nom_base = next((c for c in df_base.columns if c.upper() == 'NOME 1'), 'Nome 1')
        col_loc_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')

        resumo_base = df_base.groupby(col_rv_base).size().reset_index(name='Total na Base')
        resumo_agenda = df_agenda.groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Já Agendados')
        df_dash = pd.merge(resumo_base, resumo_agenda, left_on=col_rv_base, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Já Agendados']
        df_dash['% Conclusão'] = (df_dash['Já Agendados'] / df_dash['Total na Base'] * 100).round(1).astype(str) + '%'
        
        st.dataframe(df_dash[[col_rv_base, 'Total na Base', 'Já Agendados', 'Faltando', '% Conclusão']], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📥 Extrair Relatório Detalhado")
        agendados_set = set(df_agenda['CÓDIGO CLIENTE'].unique())
        df_extrair = df_base[[col_rv_base, col_cli_base, col_nom_base, col_loc_base]].copy()
        
        # No DataFrame do Streamlit mantemos os emojis para ficar bonito na tela
        df_extrair['STATUS'] = df_extrair[col_cli_base].apply(lambda x: "✅ Agendado" if str(x) in agendados_set else "❌ Pendente")
        
        e1, e2, _ = st.columns([1,1,2])
        with e1:
            st.download_button("📄 Exportar PDF Detalhado", data=gerar_pdf_dashboard(df_extrair), file_name="Relatorio_Engajamento.pdf", use_container_width=True)
        with e2:
            st.download_button("📥 Exportar Excel Detalhado", data=converter_para_excel(df_extrair), file_name="Relatorio_Engajamento.xlsx", use_container_width=True)

# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    if df_base is not None:
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), None)
        
        if is_admin or is_diretoria or is_analista:
            sups = sorted([s for s in df_base[col_rv_base].unique() if str(s).strip()])
            sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
        else:
            sup_sel = user_atual

        if sup_sel != "Selecione...":
            clientes_f = df_base[df_base[col_rv_base] == sup_sel]
            codigos_ag = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
            pendentes = clientes_f[~clientes_f['Cliente'].isin(codigos_ag)]
            
            lista_c = sorted(pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            if not lista_c:
                st.success("✅ Tudo agendado!")
            else:
                cliente_sel = st.selectbox("Cliente:", ["Selecione..."] + lista_c)
                if cliente_sel != "Selecione...":
                    with st.form("f_novo"):
                        d1 = st.date_input("Data da Visita:", datetime.now(fuso_br))
                        if st.form_submit_button("Salvar"):
                            cod, nom = cliente_sel.split(" - ", 1)
                            novo = pd.DataFrame([{
                                "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                                "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"),
                                "DATA": d1.strftime("%d/%m/%Y"),
                                "SUPERVISOR": sup_sel,
                                "CÓDIGO CLIENTE": cod,
                                "CLIENTE": nom,
                                "STATUS": "Planejado (X)",
                                "JUSTIFICATIVA": "-"
                            }])
                            df_a_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), novo], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_a_final)
                            st.cache_data.clear()
                            st.success("Salvo!")
                            time.sleep(1)
                            st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    if df_agenda is not None and not df_agenda.empty:
        df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual].copy() if not is_admin else df_agenda.copy()
        
        c1, c2, _ = st.columns([1,1,2])
        with c1: st.download_button("📥 Excel", data=converter_para_excel(df_f), file_name="agenda.xlsx")
        with c2: st.download_button("📄 PDF", data=gerar_pdf(df_f), file_name="agenda.pdf")

        df_f["EDITAR"] = False
        edicao = st.data_editor(df_f, key="edt_v3", hide_index=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")})
        
        marcados = edicao[edicao["EDITAR"] == True]
        if not marcados.empty:
            sel = marcados.iloc[0]
            with st.form("f_ed"):
                n_st = st.selectbox("Status:", ["Planejado (X)", "Realizado", "Reagendado"])
                n_ju = st.text_input("Obs:")
                if st.form_submit_button("Atualizar"):
                    df_agenda.loc[df_agenda['ID'] == sel['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
