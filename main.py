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
# O password abaixo é apenas para criptografia local do cookie
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
    
    /* Estilização do Card de Usuário Logado */
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
        tamanho_fonte_cabecalho = 5
        tamanho_fonte_dados = 4
        limite_texto = 25
    elif qtd_cols > 6:
        tamanho_fonte_cabecalho = 6
        tamanho_fonte_dados = 5
        limite_texto = 30
    else:
        tamanho_fonte_cabecalho = 8
        tamanho_fonte_dados = 7
        limite_texto = 40

    largura_cliente = 60  
    largura_supervisor = 30
    largura_agendado = 30
    largura_data = 18
    largura_justificativa = 50
    largura_registro = 25 
    largura_cidade = 40   
    
    especiais = []
    col_map = {str(c).upper(): c for c in cols}
    
    if "CLIENTE" in col_map: especiais.append("CLIENTE")
    if "SUPERVISOR" in col_map: especiais.append("SUPERVISOR")
    if "AGENDADO POR" in col_map: especiais.append("AGENDADO POR")
    if "DATA" in col_map: especiais.append("DATA")
    if "JUSTIFICATIVA" in col_map: especiais.append("JUSTIFICATIVA")
    if "REGISTRO" in col_map: especiais.append("REGISTRO")
    if "CIDADE" in col_map: especiais.append("CIDADE")
    
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
        if 'DATA REAGENDAMENTO' not in df_a.columns:
    df_a['DATA REAGENDAMENTO'] = "-"

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
    # Verifica se existe cookie de login salvo
    if "user_marata" in cookies:
        st.session_state.logado = True
        st.session_state.usuario = cookies["user_marata"]
    else:
        st.session_state.logado = False
        st.session_state.usuario = ""

if not st.session_state.logado:
    st.title("☕ Acesso Gestão Maratá")
    tab_login, tab_cadastro = st.tabs(["Login", "Novo Cadastro"])

    with tab_login:
        with st.form("login_form"):
            u_login = st.text_input("Usuário:").strip().upper()
            p_login = st.text_input("Senha:", type="password")
            lembrar = st.checkbox("Manter conectado")
            if st.form_submit_button("Entrar"):
                if "USUARIO" in df_usuarios.columns and "SENHA" in df_usuarios.columns:
                    valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u_login) & (df_usuarios['SENHA'].astype(str) == p_login)]
                    if not valid.empty:
                        st.session_state.logado = True
                        st.session_state.usuario = u_login
                        if lembrar:
                            cookies["user_marata"] = u_login
                            cookies.save()
                        st.rerun()
                    else:
                        st.error("Usuário ou Senha incorretos.")
                else:
                    st.error("Colunas 'USUARIO' ou 'SENHA' não encontradas na aba USUARIOS.")

    with tab_cadastro:
        with st.form("cad_form"):
            st.write("Crie sua conta")
            u_cad = st.text_input("Nome de Usuário:").strip().upper()
            p_cad = st.text_input("Defina uma Senha:", type="password")
            p_cad_conf = st.text_input("Repita a Senha:", type="password")
            
            if st.form_submit_button("Finalizar Cadastro"):
                if u_cad and p_cad and p_cad_conf:
                    if p_cad != p_cad_conf:
                        st.error("As senhas não coincidem. Por favor, verifique.")
                    else:
                        existente = False
                        if "USUARIO" in df_usuarios.columns:
                            existente = u_cad in df_usuarios['USUARIO'].str.upper().values
                        
                        if not existente:
                            novo_user = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                            df_final_u = pd.concat([df_usuarios, novo_user], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_final_u)
                            st.success("Cadastro realizado! Agora você pode fazer o login.")
                            st.cache_data.clear()
                        else:
                            st.error("Este usuário já está cadastrado.")
                else:
                    st.warning("Preencha todos os campos.")
    st.stop()

# --- PERFIL DO USUÁRIO ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

# Definindo ícone e label com base no perfil
if is_admin:
    label_display = "ADMINISTRADOR"
    user_icon = "👑"
    border_color = "#FFD700"  # Dourado para ADM
elif is_diretoria:
    label_display = f"DIRETORIA {user_atual}"
    user_icon = "📈"
    border_color = "#1E90FF"
elif is_analista:
    label_display = f"ANALISTA {user_atual}"
    user_icon = "🔬"
    border_color = "#9370DB"
else:
    label_display = f"SUPERVISOR {user_atual}"
    user_icon = "👤"
    border_color = "#ff4b4b"

# --- BARRA LATERAL ---
with st.sidebar:
    try:
        st.image("pngmarata", width=150)
    except:
        try:
            st.image("pngmarata.png", width=150)
        except:
            st.warning("Logo 'pngmarata' não encontrada.")
            
    # CARD DO USUÁRIO NO MENU LATERAL
    st.markdown(f"""
        <div class="user-card" style="border-left: 5px solid {border_color};">
            <div class="user-card-icon">{user_icon}</div>
            <div class="user-card-text">{label_display}</div>
        </div>
    """, unsafe_allow_html=True)
    
    opcoes_menu = ["📅 Agendamentos do Dia", "📋 Novo Agendamento", "🔍 Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria:
        opcoes_menu.append("📊 Dashboard de Controle")
        
    menu = st.selectbox("Menu Principal", opcoes_menu)
    
    if st.button("Sair"):
        if "user_marata" in cookies:
            del cookies["user_marata"]
            cookies.save()
        st.session_state.logado = False
        st.session_state.usuario = ""
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Limpeza em Massa")
    if df_agenda is not None and not df_agenda.empty:
        if is_admin or is_analista or is_diretoria:
            lista_sups = sorted(df_agenda['SUPERVISOR'].unique())
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups)
            if sup_limpar != "Selecione...":
                if st.button(f"⚠️ APAGAR TUDO: {sup_limpar}"):
                    df_rest = df_agenda[df_agenda['SUPERVISOR'] != sup_limpar].drop(columns=['LINHA'], errors='ignore')
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                    st.cache_data.clear()
                    st.rerun()
        else:
            if st.button(f"⚠️ APAGAR TODA MINHA AGENDA"):
                df_rest = df_agenda[df_agenda['SUPERVISOR'] != user_atual].drop(columns=['LINHA'], errors='ignore')
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                st.cache_data.clear()
                st.rerun()

# --- TÍTULO CENTRAL NO TOPO ---
st.markdown("<h4 style='text-align: center; color: white; margin-top: -50px;'>SISTEMA DE CONTROLE DE AGENDAMENTOS (SCA) - MARATÁ</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- PÁGINA: AGENDAMENTOS DO DIA ---
if menu == "📅 Agendamentos do Dia":
    st.header("📅 Agendamentos do Dia")
    hoje_str = datetime.now(fuso_br).strftime("%d/%m/%Y")
    
    if df_agenda is not None and not df_agenda.empty:
        df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
        
        if is_admin or is_diretoria:
            pass 
        elif is_analista:
            df_dia = df_dia[df_dia['ANALISTA'].str.upper() == user_atual]
        else:
            df_dia = df_dia[df_dia['SUPERVISOR'] == user_atual]

        st.columns([1, 3])[0].metric("Visitas Hoje", len(df_dia))
        
        if not df_dia.empty:
            if df_base is not None:
                col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
                df_cidades = df_base[['Cliente', col_local_base]].copy()
                df_dia = pd.merge(df_dia, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left').drop(columns=['Cliente_y'], errors='ignore')
                df_dia.rename(columns={col_local_base: 'CIDADE'}, inplace=True)

            df_dia["EDITAR"] = False
            cols_v = ['EDITAR', 'DATA', 'SUPERVISOR', 'CLIENTE', 'CIDADE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']
            
            df_display = df_dia[cols_v].copy()
            
            edicao_dia = st.data_editor(df_display, key="edit_dia", hide_index=True, use_container_width=True,
                                     column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                                     disabled=[c for c in cols_v if c != "EDITAR"])

            marcados = edicao_dia[edicao_dia["EDITAR"] == True]
            if not marcados.empty:
                sel_row = df_dia.iloc[marcados.index[0]]
                st.markdown("---")
                st.subheader(f"Atualizar Atendimento: {sel_row['CLIENTE']}")
                st_list = ["Planejado", "Realizado", "Reagendado"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                col1, col2 = st.columns(2)
                with col1: n_st = st.radio("Status Atual:", st_list, index=st_list.index(sel_row['STATUS']) if sel_row['STATUS'] in st_list else 0)
                with col2:
                    n_ju = st.selectbox("Justificativa/Observação:", ju_list, index=ju_list.index(sel_row['JUSTIFICATIVA']) if sel_row['JUSTIFICATIVA'] in ju_list else 0)
                    mot_outro = st.text_input("Especifique:") if n_ju == "OUTRO" else ""

                if st.button("💾 ATUALIZAR STATUS"):
                    final_j = mot_outro if n_ju == "OUTRO" else n_ju
                    df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, final_j]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.success("Atualizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info(f"Não há agendamentos para hoje ({hoje_str}).")
    else:
        st.warning("Nenhum dado de agenda disponível.")

# --- PÁGINA: DASHBOARD ---
elif menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento por Supervisor")
    
    if df_base is not None and df_agenda is not None:
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'Analista')
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')

        st.subheader("Filtros de Visualização")
        f_c1, f_c2 = st.columns(2)
        
        df_base_filtrada = df_base.copy()
        
        with f_c1:
            if is_admin or is_diretoria:
                lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
                ana_sel_dash = st.selectbox("Escolher Analista:", ["Todos"] + lista_analistas, key="ana_dash")
                if ana_sel_dash != "Todos":
                    df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base] == ana_sel_dash]
            else: 
                ana_sel_dash = user_atual
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base].str.upper() == user_atual]

        with f_c2:
            lista_sups_dash = sorted([str(s) for s in df_base_filtrada[col_rv_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
            sup_sel_dash = st.selectbox("Escolher Supervisor:", ["Todos"] + lista_sups_dash, key="sup_dash")
            if sup_sel_dash != "Todos":
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_rv_base] == sup_sel_dash]

        df_reg_agenda = df_agenda[['CÓDIGO CLIENTE', 'REGISTRO']].copy().drop_duplicates(subset='CÓDIGO CLIENTE', keep='last')
        df_base_detalhe = df_base_filtrada.copy()
        df_base_detalhe = pd.merge(df_base_detalhe, df_reg_agenda, left_on='Cliente', right_on='CÓDIGO CLIENTE', how='left')
        
        df_base_detalhe['STATUS AGENDAMENTO'] = df_base_detalhe['REGISTRO'].apply(
            lambda x: 'AGENDADO' if pd.notnull(x) and str(x).strip() != "" and str(x) != "-" else 'PENDENTE'
        )
        df_base_detalhe['REGISTRO'] = df_base_detalhe['REGISTRO'].fillna("-")
        
        df_relatorio_completo = df_base_detalhe[['REGISTRO', col_rv_base, 'Cliente', 'Nome 1', col_local_base, 'STATUS AGENDAMENTO']]
        df_relatorio_completo.columns = ['REGISTRO', 'SUPERVISOR', 'CÓDIGO', 'CLIENTE', 'CIDADE', 'STATUS']
        df_relatorio_completo = df_relatorio_completo.sort_values(by='STATUS')

        resumo_base = df_base_filtrada.groupby(col_rv_base).size().reset_index(name='Total na Base')
        resumo_agenda = df_agenda[df_agenda['CÓDIGO CLIENTE'].isin(df_base_filtrada['Cliente'])].groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Já Agendados')
        
        df_dash = pd.merge(resumo_base, resumo_agenda, left_on=col_rv_base, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Já Agendados'] = df_dash['Já Agendados'].astype(int)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Já Agendados']
        df_dash['% Conclusão'] = (df_dash['Já Agendados'] / df_dash['Total na Base'] * 100).round(1).astype(str) + '%'
        df_dash = df_dash[[col_rv_base, 'Total na Base', 'Já Agendados', 'Faltando', '% Conclusão']]
        df_dash.columns = ['SUPERVISOR', 'CLIENTES NA BASE', 'CLIENTES AGENDADOS', 'FALTANDO', '% DE ADESÃO']
        
        exp_c1, exp_c2, _ = st.columns([1, 1, 2])
        with exp_c1:
            st.download_button("📥 Relatório Detalhado (Excel)", data=converter_para_excel(df_relatorio_completo), file_name="detalhamento_agendamentos.xlsx")
        with exp_c2:
            try:
                st.download_button("📄 Relatório Detalhado (PDF)", data=gerar_pdf(df_relatorio_completo, tipo_relatorio="DASH"), file_name="detalhamento_agendamentos.pdf")
            except:
                st.error("Erro ao gerar PDF do detalhamento")
        
        st.dataframe(df_dash, use_container_width=True, hide_index=True)
        
        c1, c2, c3, c4 = st.columns(4)
        total_base = df_dash['CLIENTES NA BASE'].sum()
        total_agendados = df_dash['CLIENTES AGENDADOS'].sum()
        total_pendente = df_dash['FALTANDO'].sum()
        percent_adesao = (total_agendados / total_base * 100) if total_base > 0 else 0
        
        c1.metric("Total Clientes Base (Filtro)", total_base)
        c2.metric("Total Agendados (Filtro)", total_agendados)
        c3.metric("Pendente Total (Filtro)", total_pendente)
        c4.metric("% Adesão Total", f"{percent_adesao:.1f}%")

        # --- NOVA FUNÇÃO: RANKING DE ENGAJAMENTO (ADICIONADA AQUI) ---
        st.markdown("---")
        st.subheader("🏆 Ranking de Engajamento")
        
        df_ranking = df_dash.copy()
        # Converter string de porcentagem para float para ordenar corretamente
        df_ranking['VALOR_NUM'] = df_ranking['% DE ADESÃO'].str.replace('%', '').astype(float)
        df_ranking = df_ranking.sort_values(by='VALOR_NUM', ascending=False).reset_index(drop=True)
        df_ranking.index += 1  # Ranking começa em 1
        
        # Adicionar medalhas aos 3 primeiros
        def medalha(pos):
            if pos == 1: return "🥇"
            if pos == 2: return "🥈"
            if pos == 3: return "🥉"
            return str(pos) + "º"
            
        df_ranking['POSIÇÃO'] = [medalha(i) for i in df_ranking.index]
        df_ranking_view = df_ranking[['POSIÇÃO', 'SUPERVISOR', 'CLIENTES AGENDADOS', '% DE ADESÃO']]
        
        st.table(df_ranking_view)
        
    else:
        st.error("Dados insuficientes para gerar o Dashboard.")

# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    if df_base is not None:
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), None)
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')

        if is_admin or is_diretoria:
            if col_ana_base:
                lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
                ana_sel = st.selectbox("Filtrar por Analista:", ["Todos"] + lista_analistas)
                if ana_sel == "Todos":
                    sups = sorted([s for s in df_base[col_rv_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
                else:
                    sups = sorted([s for s in df_base[df_base[col_ana_base] == ana_sel][col_rv_base].unique() if str(s).strip()])
            else:
                st.error("Coluna 'Analista' não encontrada na aba BASE.")
                sups = []
            sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
        elif is_analista:
            if col_ana_base:
                sups = sorted([s for s in df_base[df_base[col_ana_base].str.upper() == user_atual][col_rv_base].unique() if str(s).strip()])
            else:
                sups = []
            sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
        else:
            sup_sel = user_atual
            st.info(f"Agendando para: {user_atual}")

        if sup_sel != "Selecione...":
            clientes_f = df_base[df_base[col_rv_base] == sup_sel]
            codigos_agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
            clientes_pendentes = clientes_f[~clientes_f['Cliente'].isin(codigos_agendados)]
            
            m1, m2, m3, m4 = st.columns(4)
            n_total = len(clientes_f)
            n_agendados = len(codigos_agendados)
            n_pendentes = len(clientes_pendentes)
            perc_sup = (n_agendados / n_total * 100) if n_total > 0 else 0
            
            m1.metric("Total na Base", n_total)
            m2.metric("Já Agendados", n_agendados)
            m3.metric("Faltando", n_pendentes)
            m4.metric("% Adesão", f"{perc_sup:.1f}%")
            
            analista_vinc = NOME_ANALISTA
            if col_ana_base in clientes_f.columns:
                val_analista = clientes_f[col_ana_base].iloc[0]
                if str(val_analista).strip() and str(val_analista).lower() != 'nan':
                    analista_vinc = str(val_analista).upper()

            lista_c = sorted(clientes_pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            
            if not lista_c:
                st.success("✅ Todos os clientes desta base já foram agendados!")
            else:
                cliente_sel = st.selectbox("Selecione o Cliente (Apenas Pendentes):", ["Selecione..."] + lista_c)
                if cliente_sel != "Selecione...":
                    qtd_visitas = st.number_input("Quantidade de visitas (Máx 4):", min_value=1, max_value=4, value=1)
                    with st.form("form_novo_v"):
                        cols_datas = st.columns(qtd_visitas)
                        datas_sel = []
                        for i in range(qtd_visitas):
                            with cols_datas[i]:
                                d = st.date_input(f"Data {i+1}:", datetime.now(fuso_br), key=f"d_{i}")
                                datas_sel.append(d)
                        if st.form_submit_button("💾 SALVAR AGENDAMENTOS"):
                            cod_c, nom_c = cliente_sel.split(" - ", 1)
                            agora = datetime.now(fuso_br)
                            novas_linhas = []
                            for i, dt in enumerate(datas_sel):
                                nid = (agora + timedelta(seconds=i)).strftime("%Y%m%d%H%M%S") + str(i)
                                novas_linhas.append({
                                    "ID": nid, 
                                    "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), 
                                    "DATA": dt.strftime("%d/%m/%Y"),
                                    "ANALISTA": analista_vinc, 
                                    "SUPERVISOR": sup_sel, 
                                    "CÓDIGO CLIENTE": cod_c, 
                                    "CLIENTE": nom_c, 
                                    "JUSTIFICATIVA": "-", 
                                    "STATUS": "Planejado",
                                    "AGENDADO POR": user_atual 
                                })
                            df_final_a = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas_linhas)], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                            st.cache_data.clear()
                            st.success(f"✅ {qtd_visitas} visita(s) salva(s)!")
                            time.sleep(1)
                            st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    if df_agenda is not None and not df_agenda.empty:
        if is_admin or is_diretoria:
            lista_ana_age = sorted([str(a) for a in df_agenda['ANALISTA'].unique() if str(a).strip() and str(a).lower() != 'nan'])
            ana_filtro = st.selectbox("Filtrar Agenda por Analista:", ["Todos"] + lista_ana_age)
            df_temp = df_agenda.copy()
            if ana_filtro != "Todos":
                df_temp = df_temp[df_temp['ANALISTA'] == ana_filtro]
            f_sup = st.selectbox("Ver agenda de:", ["Todos"] + sorted(df_temp['SUPERVISOR'].unique()))
            df_f = df_temp.copy() if f_sup == "Todos" else df_temp[df_temp['SUPERVISOR'] == f_sup]
        elif is_analista:
            df_f = df_agenda[df_agenda['ANALISTA'].str.upper() == user_atual].copy()
            f_sup = st.selectbox("Ver agenda de:", ["Todos"] + sorted(df_f['SUPERVISOR'].unique()))
            if f_sup != "Todos":
                df_f = df_f[df_f['SUPERVISOR'] == f_sup]
        else:
            df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual].copy()

        if 'ANALISTA' not in df_f.columns: df_f['ANALISTA'] = "-"
        if 'AGENDADO POR' not in df_f.columns: df_f['AGENDADO POR'] = "-"
        
        if df_base is not None:
            col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
            df_cidades = df_base[['Cliente', col_local_base]].copy()
            df_f = pd.merge(df_f, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left').drop(columns=['Cliente_y'], errors='ignore')
            df_f.rename(columns={col_local_base: 'CIDADE'}, inplace=True)
        
        cols_exp = ['REGISTRO', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'CIDADE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']
        df_exp = df_f[cols_exp]
        
        c1, c2, _ = st.columns([0.15, 0.15, 0.7])
        with c1: st.download_button("📥 Excel", data=converter_para_excel(df_exp), file_name="agenda.xlsx")
        with c2: 
            try: 
                st.download_button("📄 PDF", data=gerar_pdf(df_exp, tipo_relatorio="AGENDA"), file_name="agenda.pdf")
            except: st.error("Erro ao gerar PDF")

        df_f["EDITAR"] = False
        cols_v = ['EDITAR', 'REGISTRO', 'DATA', 'REAGENDADO PARA','ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']
        
        df_display = df_f[cols_v].copy()
        try:
            df_display['REG_TEMP'] = pd.to_datetime(df_display['REGISTRO'], dayfirst=True)
            df_display = df_display.sort_values(by='REG_TEMP', ascending=False).drop(columns=['REG_TEMP'])
        except:
            df_display = df_display.sort_values(by='REGISTRO', ascending=False)

        edicao = st.data_editor(df_display, key="edit_v12", hide_index=True, use_container_width=True,
                                 column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                                 disabled=[c for c in cols_v if c != "EDITAR"])

        marcados = edicao[edicao["EDITAR"] == True]
        if not marcados.empty:
            sel_row = df_f.loc[df_f['REGISTRO'] == marcados.iloc[0]['REGISTRO']].iloc[0]
            st.markdown("---")
            st.subheader(f"Editar: {sel_row['CLIENTE']}")
            st_list = ["Planejado", "Realizado", "Reagendado"]
            ju_list = list(df_just.iloc[:, 0].dropna().unique())
            if "OUTRO" not in ju_list: ju_list.append("OUTRO")
            col1, col2 = st.columns(2)
            with col1: n_st = st.radio("Status:", st_list, index=st_list.index(sel_row['STATUS']) if sel_row['STATUS'] in st_list else 0)
                nova_data = None
if n_st == "Reagendado":
    nova_data = st.date_input(
        "Nova data de reagendamento:",
        value=datetime.now(fuso_br)
    )

            with col2:
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(sel_row['JUSTIFICATIVA']) if sel_row['JUSTIFICATIVA'] in ju_list else 0)
                mot_outro = st.text_input("Qual o motivo?") if n_ju == "OUTRO" else ""

           with st.form("save_form"):
    b1, b2 = st.columns(2)

    if b1.form_submit_button("💾 SALVAR"):
        final_j = mot_outro if n_ju == "OUTRO" else n_ju

        # Atualiza status e justificativa
        df_agenda.loc[
            df_agenda['ID'] == sel_row['ID'],
            ['STATUS', 'JUSTIFICATIVA']
        ] = [n_st, final_j]

        # Atualiza data de reagendamento apenas se for Reagendado
        if n_st == "Reagendado" and nova_data:
            df_agenda.loc[
                df_agenda['ID'] == sel_row['ID'],
                'DATA REAGENDAMENTO'
            ] = nova_data.strftime("%d/%m/%Y")
        else:
            df_agenda.loc[
                df_agenda['ID'] == sel_row['ID'],
                'DATA REAGENDAMENTO'
            ] = "-"

        conn.update(
            spreadsheet=url_planilha,
            worksheet="AGENDA",
            data=df_agenda.drop(columns=['LINHA'], errors='ignore')
        )
        st.cache_data.clear()
        st.rerun()

    if b2.form_submit_button("🗑️ EXCLUIR"):
        df_novo_a = df_agenda[df_agenda['ID'] != sel_row['ID']].drop(
            columns=['LINHA'], errors='ignore'
        )
        conn.update(
            spreadsheet=url_planilha,
            worksheet="AGENDA",
            data=df_novo_a
        )
        st.cache_data.clear()
        st.rerun()

    else:
        st.info("Nenhum registro encontrado.")
