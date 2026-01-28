import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import io
from fpdf import FPDF
import pytz
import time
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# --- CUSTOMIZAÇÃO DE CORES E CARDS (CSS) ---
st.markdown("""
    <style>
        /* Fundo da área principal - VERDE */
        .stApp {
            background-color: #04780D;
        }
        
        /* Fundo do Menu Lateral (Sidebar) - AZUL ESCURO */
        [data-testid="stSidebar"] {
            background-color: #001F3F;
        }

        /* Ajuste de cor de textos da Sidebar para branco */
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] h3 {
            color: white !important;
        }

        /* Ajuste de cor de títulos na área principal para preto */
        h1, h2, h3, h4, h5, h6, p, span {
            color: #000000 !important;
        }

        /* CUSTOMIZAÇÃO DOS CARDS (METRICS) */
        [data-testid="stMetric"] {
            background-color: #F0F2F6; /* Cor de fundo clara para o card */
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
            border-left: 5px solid #001F3F; /* Faixa azul na lateral para combinar */
        }
        
        /* Ajuste do texto dentro do card para não sumir */
        [data-testid="stMetricLabel"] p {
            color: #333333 !important;
            font-weight: bold !important;
        }
        [data-testid="stMetricValue"] div {
            color: #001F3F !important;
        }

        /* Cor dos botões e abas - TEXTO DOS BOTÕES PARA BRANCO */
        .stButton>button, .stDownloadButton>button {
            border-radius: 5px;
            color: #FFFFFF !important;
            background-color: #001F3F; 
        }
        
        .stButton>button p, .stDownloadButton>button p {
            color: #FFFFFF !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }

        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: rgba(0, 0, 0, 0.05);
            border-radius: 4px 4px 0px 0px;
            color: #FFFFFF;
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

    largura_cliente, largura_supervisor, largura_agendado = 60, 30, 30
    largura_data, largura_justificativa, largura_registro, largura_cidade = 18, 50, 25, 40
    
    especiais = [c for c in ["CLIENTE", "SUPERVISOR", "AGENDADO POR", "DATA", "JUSTIFICATIVA", "REGISTRO", "CIDADE"] if c in [str(x).upper() for x in cols]]
    
    ocupado = 0
    if "CLIENTE" in especiais: ocupado += largura_cliente
    if "SUPERVISOR" in especiais: ocupado += largura_supervisor
    if "AGENDADO POR" in especiais: ocupado += largura_agendado
    if "DATA" in especiais: ocupado += largura_data
    if "JUSTIFICATIVA" in especiais: ocupado += largura_justificativa
    if "REGISTRO" in especiais: ocupado += largura_registro
    if "CIDADE" in especiais: ocupado += largura_cidade
    
    outras_cols_count = len(cols) - len(especiais)
    largura_padrao = (largura_total - ocupado) / outras_cols_count if outras_cols_count > 0 else 0
    
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
        else: w = largura_padrao
        pdf.cell(w, 6, str(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', tamanho_fonte_dados) 
    for index, row in df_pdf.iterrows():
        for i, item in enumerate(row):
            col_name = str(cols[i]).upper()
            if col_name == "CLIENTE": w, limit = largura_cliente, 50
            elif col_name == "SUPERVISOR": w, limit = largura_supervisor, 30
            elif col_name == "AGENDADO POR": w, limit = largura_agendado, 30
            elif col_name == "DATA": w, limit = largura_data, 12
            elif col_name == "JUSTIFICATIVA": w, limit = largura_justificativa, 60
            elif col_name == "REGISTRO": w, limit = largura_registro, 20
            elif col_name == "CIDADE": w, limit = largura_cidade, 35
            else: w, limit = largura_padrao, limite_texto
            
            texto = str(item)[:limit].encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(w, 5, texto, border=1)
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
            u_cad = st.text_input("Nome de Usuário:").strip().upper()
            p_cad = st.text_input("Defina uma Senha:", type="password")
            p_cad_conf = st.text_input("Repita a Senha:", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                if u_cad and p_cad == p_cad_conf:
                    if "USUARIO" in df_usuarios.columns and u_cad not in df_usuarios['USUARIO'].str.upper().values:
                        novo_user = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                        df_final_u = pd.concat([df_usuarios, novo_user], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_final_u)
                        st.success("Cadastro realizado!")
                        st.cache_data.clear()
                    else: st.error("Usuário já existe.")
                else: st.warning("Erro no preenchimento.")
    st.stop()

user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())
label_display = "ADMINISTRADOR" if is_admin else f"DIRETORIA {user_atual}" if is_diretoria else f"ANALISTA {user_atual}" if is_analista else f"SUPERVISOR {user_atual}"

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown(f"👤 **{label_display}**")
    opcoes_menu = ["Novo Agendamento", "Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria: opcoes_menu.append("📊 Dashboard de Controle")
    menu = st.selectbox("Menu Principal", opcoes_menu)
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()
    st.markdown("---")
    if is_admin or is_analista or is_diretoria:
        if df_agenda is not None and not df_agenda.empty:
            lista_sups = sorted(df_agenda['SUPERVISOR'].unique())
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups)
            if sup_limpar != "Selecione..." and st.button(f"⚠️ APAGAR TUDO: {sup_limpar}"):
                df_rest = df_agenda[df_agenda['SUPERVISOR'] != sup_limpar].drop(columns=['LINHA'], errors='ignore')
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                st.cache_data.clear()
                st.rerun()

st.markdown("<h4 style='text-align: center; color: #000000; margin-top: -50px;'>SISTEMA DE CONTROLE DE AGENDAMENTOS (SCA) - MARATÁ</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- PÁGINA: DASHBOARD ---
if menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento por Supervisor")
    if df_base is not None and df_agenda is not None:
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'Analista')
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
        
        f_c1, f_c2 = st.columns(2)
        df_base_filtrada = df_base.copy()
        with f_c1:
            if is_admin or is_diretoria:
                lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
                ana_sel_dash = st.selectbox("Escolher Analista:", ["Todos"] + lista_analistas, key="ana_dash")
                if ana_sel_dash != "Todos": df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base] == ana_sel_dash]
            else: df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base].str.upper() == user_atual]
        with f_c2:
            lista_sups_dash = sorted([str(s) for s in df_base_filtrada[col_rv_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
            sup_sel_dash = st.selectbox("Escolher Supervisor:", ["Todos"] + lista_sups_dash, key="sup_dash")
            if sup_sel_dash != "Todos": df_base_filtrada = df_base_filtrada[df_base_filtrada[col_rv_base] == sup_sel_dash]

        df_reg_agenda = df_agenda[['CÓDIGO CLIENTE', 'REGISTRO']].copy().drop_duplicates(subset='CÓDIGO CLIENTE', keep='last')
        df_base_detalhe = pd.merge(df_base_filtrada.copy(), df_reg_agenda, left_on='Cliente', right_on='CÓDIGO CLIENTE', how='left')
        df_base_detalhe['STATUS AGENDAMENTO'] = df_base_detalhe['REGISTRO'].apply(lambda x: 'AGENDADO' if pd.notnull(x) and str(x).strip() != "" and str(x) != "-" else 'PENDENTE')
        df_relatorio_completo = df_base_detalhe[['REGISTRO', col_rv_base, 'Cliente', 'Nome 1', col_local_base, 'STATUS AGENDAMENTO']]
        df_relatorio_completo.columns = ['REGISTRO', 'SUPERVISOR', 'CÓDIGO', 'CLIENTE', 'CIDADE', 'STATUS']
        
        resumo_base = df_base_filtrada.groupby(col_rv_base).size().reset_index(name='Total na Base')
        resumo_agenda = df_agenda[df_agenda['CÓDIGO CLIENTE'].isin(df_base_filtrada['Cliente'])].groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Já Agendados')
        df_dash = pd.merge(resumo_base, resumo_agenda, left_on=col_rv_base, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Já Agendados']
        df_dash['% DE ADESÃO'] = (df_dash['Já Agendados'] / df_dash['Total na Base'] * 100).round(1).astype(str) + '%'
        df_dash = df_dash[[col_rv_base, 'Total na Base', 'Já Agendados', 'Faltando', '% DE ADESÃO']]
        df_dash.columns = ['SUPERVISOR', 'CLIENTES NA BASE', 'CLIENTES AGENDADOS', 'FALTANDO', '% DE ADESÃO']

        exp_c1, exp_c2, _ = st.columns([1, 1, 2])
        with exp_c1: st.download_button("📥 Relatório Detalhado (Excel)", data=converter_para_excel(df_relatorio_completo), file_name="detalhamento.xlsx")
        with exp_c2: st.download_button("📄 Relatório Detalhado (PDF)", data=gerar_pdf(df_relatorio_completo, tipo_relatorio="DASH"), file_name="detalhamento.pdf")
        
        st.dataframe(df_dash, use_container_width=True, hide_index=True)
        
        # CARDS COM FUNDO (MÉTRICAS)
        c1, c2, c3, c4 = st.columns(4)
        total_base = df_dash['CLIENTES NA BASE'].sum()
        total_agendados = df_dash['CLIENTES AGENDADOS'].sum()
        total_pendente = df_dash['FALTANDO'].sum()
        percent_adesao = (total_agendados / total_base * 100) if total_base > 0 else 0
        
        c1.metric("Total Clientes Base (Filtro)", int(total_base))
        c2.metric("Total Agendados (Filtro)", int(total_agendados))
        c3.metric("Pendente Total (Filtro)", int(total_pendente))
        c4.metric("% Adesão Total", f"{percent_adesao:.1f}%")
        
    else: st.error("Dados insuficientes.")

# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    if df_base is not None:
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), None)
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        if is_admin or is_diretoria:
            lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
            ana_sel = st.selectbox("Filtrar por Analista:", ["Todos"] + lista_analistas)
            sups = sorted([s for s in df_base[(df_base[col_ana_base] == ana_sel) if ana_sel != "Todos" else True][col_rv_base].unique() if str(s).strip()])
            sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
        elif is_analista:
            sups = sorted([s for s in df_base[df_base[col_ana_base].str.upper() == user_atual][col_rv_base].unique() if str(s).strip()])
            sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
        else: sup_sel = user_atual
        
        if sup_sel != "Selecione...":
            clientes_f = df_base[df_base[col_rv_base] == sup_sel]
            codigos_agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
            clientes_pendentes = clientes_f[~clientes_f['Cliente'].isin(codigos_agendados)]
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total na Base", len(clientes_f))
            m2.metric("Já Agendados", len(codigos_agendados))
            m3.metric("Faltando", len(clientes_pendentes))
            m4.metric("% Adesão", f"{(len(codigos_agendados)/len(clientes_f)*100):.1f}%" if len(clientes_f)>0 else "0%")
            
            lista_c = sorted(clientes_pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            if not lista_c: st.success("✅ Tudo agendado!")
            else:
                cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)
                if cliente_sel != "Selecione...":
                    qtd = st.number_input("Quantidade de visitas (Máx 4):", 1, 4, 1)
                    with st.form("form_novo"):
                        cols_d = st.columns(qtd)
                        datas = [cols_d[i].date_input(f"Data {i+1}", datetime.now(fuso_br), key=f"d{i}") for i in range(qtd)]
                        if st.form_submit_button("💾 SALVAR"):
                            cod_c, nom_c = cliente_sel.split(" - ", 1)
                            novas = [{"ID": (datetime.now(fuso_br)+timedelta(seconds=i)).strftime("%Y%m%d%H%M%S")+str(i), "REGISTRO": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M"), "DATA": dt.strftime("%d/%m/%Y"), "ANALISTA": user_atual, "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)", "AGENDADO POR": user_atual} for i, dt in enumerate(datas)]
                            df_final_a = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas)], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                            st.cache_data.clear()
                            st.success("Salvo!")
                            time.sleep(1)
                            st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    if df_agenda is not None and not df_agenda.empty:
        df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual].copy() if not (is_admin or is_analista or is_diretoria) else df_agenda.copy()
        if is_admin or is_diretoria or is_analista:
            f_sup = st.selectbox("Ver agenda de:", ["Todos"] + sorted(df_f['SUPERVISOR'].unique()))
            if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]
        
        df_exp = df_f[['REGISTRO', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']]
        c1, c2, _ = st.columns([1,1,2])
        with c1: st.download_button("📥 Excel", data=converter_para_excel(df_exp), file_name="agenda.xlsx")
        with c2: st.download_button("📄 PDF", data=gerar_pdf(df_exp, tipo_relatorio="AGENDA"), file_name="agenda.pdf")

        df_f["EDITAR"] = False
        df_disp = df_f[['EDITAR', 'REGISTRO', 'DATA', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']].copy().sort_values(by='REGISTRO', ascending=False)
        edicao = st.data_editor(df_disp, key="ed_v1", hide_index=True, use_container_width=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")}, disabled=['REGISTRO', 'DATA', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS'])
        
        marcados = edicao[edicao["EDITAR"] == True]
        if not marcados.empty:
            sel_row = df_f[df_f['REGISTRO'] == marcados.iloc[0]['REGISTRO']].iloc[0]
            st.subheader(f"Editar: {sel_row['CLIENTE']}")
            ju_list = list(df_just.iloc[:, 0].dropna().unique()) + ["OUTRO"]
            col1, col2 = st.columns(2)
            n_st = col1.radio("Status:", ["Planejado (X)", "Realizado", "Reagendado"], index=0)
            n_ju = col2.selectbox("Justificativa:", ju_list)
            if st.button("💾 SALVAR ALTERAÇÃO"):
                df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                st.cache_data.clear()
                st.rerun()
    else: st.info("Vazio.")
