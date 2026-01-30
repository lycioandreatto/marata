import streamlit as st
from geoloc import capturar_coordenadas
import numpy as np
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import io
import uuid
from fpdf import FPDF
import pytz
import time
import os
from streamlit_cookies_manager import EncryptedCookieManager

# --- COLE A FUNÇÃO AQUI (LINHA 16 APROX.) ---

# --- MAPEAMENTO DE CONTATOS (Fácil de alterar) ---
MAPA_EMAILS = {
    "BARBARA": ["barbara.costa@marata.com.br", "kaio.gomes@marata.com.br","marciajanaina@marata.com.br"],
    "THAIS": ["thais.oliveira@marata.com.br","marciajanaina@marata.com.br"],
    "REGIANE": ["regiane.santana@marata.com.br","marciajanaina@marata.com.br"],
    "ALLANA": ["allana.menezes@marata.com.br", "danilo.matos@marata.com.br","marciajanaina@marata.com.br"],
    "ROBERIO": ["roberio@marata.com.br", "dione.lima@marata.com.br","marciajanaina@marata.com.br"]
}

# E-mails que sempre recebem
EMAILS_GESTAO = ["lycio.oliveira@marata.com.br"]

def enviar_resumo_rota(destinatarios_lista, vendedor, dados_resumo, nome_analista, taxa, hora, link):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    try:
        email_origem = st.secrets["email"]["sender_email"]
        senha_origem = st.secrets["email"]["sender_password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        
        msg = MIMEMultipart()
        msg['From'] = f"MARATÁ <{email_origem}>"
        msg['To'] = destinatarios_lista 
        msg['Subject'] = f"✅ Rota Finalizada - {vendedor} ({datetime.now().strftime('%d/%m')})"

        saudacao = nome_analista.title() if nome_analista != "NÃO LOCALIZADO" else "Gestão Maratá"

        corpo = f"""
        Olá, {saudacao},
        
        O vendedor {vendedor} acaba de finalizar a rota do dia.
        
        📊 RESUMO DE PERFORMANCE:
        ------------------------------------------
        - Total de Clientes na Agenda: {dados_resumo['total']}
        - Visitas Realizadas: {dados_resumo['realizados']}
        - Visitas com Pedido: {dados_resumo['pedidos']}
        - Clientes Pendentes: {dados_resumo['pendentes']}
        - Taxa de Conversão: {taxa:.1f}% (Pedidos / Visitas)
        
        📍 DADOS DE FINALIZAÇÃO:
        ------------------------------------------
        - Hora do Envio: {hora}
        - Localização Final: {link}
        
        E-mail gerado automaticamente pelo Sistema Maratá GVP.
        """
        msg.attach(MIMEText(corpo, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_origem, senha_origem)
        server.sendmail(email_origem, destinatarios_lista.split(','), msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return False

# --- CONTINUAÇÃO DO SEU CÓDIGO (calcular_distancia, etc) ---



def calcular_distancia(lat1, lon1, lat2, lon2):
    # Raio da Terra em KM
    R = 6371.0
    
    dlat = np.radians(float(lat2) - float(lat1))
    dlon = np.radians(float(lon2) - float(lon1))
    
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(float(lat1))) * np.cos(np.radians(float(lat2))) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distancia = R * c * 1000 # Retorna em Metros
    return distancia

# --- CONFIGURAÇÃO DE COOKIES (Lembrar Login) ---
# O password abaixo é apenas para criptografia local do cookie
cookies = EncryptedCookieManager(password="marata_secret_key_2026")
if not cookies.ready():
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Maratá - GVP", page_icon="📅", layout="wide")

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
LISTA_ANALISTA = ["BARBARA","THAIS","ROBERIO","CAROL","REGIANE","ALLANA"]
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
        if 'COORDENADAS' not in df_b.columns:
            df_b['COORDENADAS'] = "0, 0"
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

# --- CONFIGURAÇÃO DE ACESSOS (EDITE AQUI) ---
NOME_ADMIN = "lycio"         # Você (Admin)
NOME_DIRETORIA = "aldo"         # Aldo
LISTA_ANALISTA = ["Barbara", "Thais","Allana","Roberio","Regiane","Carol"] 
LISTA_SUPERVISORES = ["Francisco", "Teste"] 
LISTA_VENDEDORES = ["Carlos Antonio", "Rita", "Saraiva","Jose Carlos"]     

# --- SISTEMA DE ACESSO ---
if "logado" not in st.session_state:
    if "user_marata" in cookies:
        st.session_state.logado = True
        st.session_state.usuario = cookies["user_marata"]
    else:
        st.session_state.logado = False
        st.session_state.usuario = ""

if not st.session_state.logado:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
            <img src="https://raw.githubusercontent.com/lycioandreatto/marata/main/pngmarata" width="60">
            <h1 style="color: #000C75; margin: 0;">GESTÃO DE VISITAS PDV</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

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
                        st.error("As senhas não coincidem.")
                    else:
                        existente = False
                        if "USUARIO" in df_usuarios.columns:
                            existente = u_cad in df_usuarios['USUARIO'].str.upper().values
                        
                        if not existente:
                            novo_user = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                            df_final_u = pd.concat([df_usuarios, novo_user], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_final_u)
                            st.cache_data.clear()
                            st.success("Cadastro realizado!")
                        else:
                            st.error("Este usuário já está cadastrado.")
    st.stop()

# --- DEFINIÇÃO DE PERFIS E HIERARQUIA ---
user_atual = st.session_state.usuario.upper()

is_admin = (user_atual == NOME_ADMIN.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())
is_analista = (user_atual in [n.upper() for n in LISTA_ANALISTA])
is_supervisor = (user_atual in [n.upper() for n in LISTA_SUPERVISORES])
is_vendedor = (user_atual in [n.upper() for n in LISTA_VENDEDORES])

eh_gestao = is_admin or is_analista or is_diretoria

# --- VALIDAÇÃO DE GPS ---
if "lat" not in st.session_state:
    with st.container():
        lat, lon = capturar_coordenadas()
        if lat and lon:
            st.session_state.lat = lat
            st.session_state.lon = lon
            st.success(f"📍 GPS Ativo")
            time.sleep(1)
            st.rerun()
        else:
            if eh_gestao:
                st.session_state.lat = 0.0
                st.session_state.lon = 0.0
                st.info("ℹ️ Perfil Gestão: GPS ignorado.")
                st.rerun()
            else:
                st.warning("⚠️ **Acesso Negado.** Geolocalização obrigatória.")
                if st.button("🔄 Tentar novamente", key="retry_gps"):
                    st.rerun()
                st.stop()

# --- CONFIGURAÇÃO VISUAL DO PERFIL ---
if is_admin:
    label_display = "ADMINISTRADOR"; user_icon = "👑"; border_color = "#FFD700"
elif is_diretoria:
    label_display = f"{user_atual} | DIRETORIA"; user_icon = "📈"; border_color = "#1E90FF"
elif is_analista:
    label_display = f"{user_atual} | ANALISTA"; user_icon = "🔬"; border_color = "#9370DB"
elif is_supervisor:
    label_display = f"{user_atual} | SUPERVISOR"; user_icon = "👔"; border_color = "#2ECC71"
else:
    label_display = f"{user_atual} | VENDEDOR"; user_icon = "👤"; border_color = "#ff4b4b"

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown(f"""
        <div class="user-card" style="border-left: 5px solid {border_color};">
            <div class="user-card-icon">{user_icon}</div>
            <div class="user-card-text">{label_display}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Texto dinâmico do menu conforme perfil
    if eh_gestao:
        texto_ver_agenda = "🔍 Agenda Geral"
    elif is_supervisor:
        texto_ver_agenda = "🔍 Agenda da Minha Equipe"
    else:
        texto_ver_agenda = "🔍 Minha Agenda de Visitas"

    # 1. Lista base de opções (acesso comum)
    opcoes_menu = ["📅 Agendamentos do Dia", "📋 Novo Agendamento", texto_ver_agenda]
    
    # 2. Trava de segurança: Desempenho de Vendas apenas para o Lycio
    # Ajuste o nome "LYCIO" para como ele aparece exatamente no seu st.session_state.usuario
    if user_atual.upper() == "LYCIO":
        opcoes_menu.append("📊 Desempenho de Vendas")
    
    # 3. Opções exclusivas de Gestão/Admin
    if eh_gestao:
        opcoes_menu.append("📊 Dashboard de Controle")
        
    menu = st.selectbox("Menu Principal", opcoes_menu)
    
    # Padronização interna para o código
    if menu == texto_ver_agenda:
        menu_interna = "🔍 Ver/Editar Minha Agenda"
    else:
        menu_interna = menu 

    # Botão Sair
    if st.button("Sair", key="btn_logout_sidebar"):
        if "user_marata" in cookies:
            del cookies["user_marata"]
            cookies.save()
        st.session_state.logado = False
        st.session_state.usuario = ""
        st.cache_data.clear()
        st.rerun()
        
    for _ in range(5): st.sidebar.write("")

    # --- SEÇÃO DE LIMPEZA (SÓ ADMIN) ---
    if is_admin:
        st.markdown("---")
        st.subheader("🗑️ Limpeza em Massa")
        if df_agenda is not None and not df_agenda.empty:
            # Filtro para evitar sups nulos ou duplicados no selectbox
            df_limpeza = df_agenda.drop_duplicates(subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'])
            lista_sups_limpar = sorted([str(x) for x in df_limpeza['SUPERVISOR'].unique() if x])
            
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups_limpar, key="sel_limpeza_admin")

            if sup_limpar != "Selecione...":
                confirma = st.popover(f"⚠️ APAGAR: {sup_limpar}")
                if confirma.button(f"Confirmar Exclusão de {sup_limpar}", key="btn_conf_limpeza"):
                    df_rest = df_agenda[df_agenda['SUPERVISOR'] != sup_limpar].copy()
                    
                    # Garante que não suba duplicados ao limpar
                    df_rest = df_rest.drop_duplicates(subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'])
                    
                    conn.update(
                        spreadsheet=url_planilha, 
                        worksheet="AGENDA", 
                        data=df_rest.drop(columns=['LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'dist_val_calc'], errors='ignore')
                    )
                    st.cache_data.clear()
                    st.success("Agenda limpa!")
                    time.sleep(1)
                    st.rerun()

# --- TÍTULO CENTRAL NO TOPO ---
st.markdown("<h4 style='text-align: center; color: black; margin-top: -110px;'>GESTÃO DE VISITAS PDV (GVP) - MARATÁ</h4>", unsafe_allow_html=True)
st.markdown("---")

# Mapeia menu_interna de volta para menu para o restante do código
menu = menu_interna

# --- PÁGINA: AGENDAMENTOS DO DIA ---
# --- PÁGINA: AGENDAMENTOS DO DIA ---
if menu == "📅 Agendamentos do Dia":
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("📅 Agendamentos do Dia")
    
    with col_btn:
        if st.button("🔄 Atualizar Agenda", key="btn_refresh_dia"):
            st.cache_data.clear()
            st.rerun()

    hoje_str = datetime.now(fuso_br).strftime("%d/%m/%Y")
    
    if df_agenda is not None and not df_agenda.empty:
        # --- PASSO 1: LIMPEZA DE DUPLICIDADES E RESET DE ÍNDICE ---
        df_agenda = df_agenda.drop_duplicates(
            subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'], 
            keep='first'
        ).reset_index(drop=True)

        col_aprov_plan = next((c for c in df_agenda.columns if "APROVA" in c.upper() and "PLAN" in c.upper() or c.upper() == "APROVACAO"), "APROVACAO")
        col_aprov_exec = "VALIDACAO_GESTAO"
        col_just = "JUSTIFICATIVA"
        
        if col_aprov_exec not in df_agenda.columns: df_agenda[col_aprov_exec] = "PENDENTE"
        if col_just not in df_agenda.columns: df_agenda[col_just] = ""

        # --- PASSO 2: FILTROS DO DIA ---
        df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
        df_dia = df_dia[df_dia[col_aprov_plan].astype(str).str.upper() == "APROVADO"]
        
        if not (is_admin or is_diretoria):
            if is_analista: 
                df_dia = df_dia[df_dia['ANALISTA'].astype(str).str.upper() == user_atual.upper()]
            elif is_supervisor: 
                df_dia = df_dia[df_dia['SUPERVISOR'].astype(str).str.upper() == user_atual.upper()]
            else: 
                df_dia = df_dia[df_dia['VENDEDOR'].astype(str).str.upper() == user_atual.upper()]

        # IMPORTANTE: Resetar índice após filtrar o dia para o editor não se perder
        df_dia = df_dia.reset_index(drop=True)

        # --- MÉTRICAS ---
        t_hoje = len(df_dia)
        t_realizado = len(df_dia[df_dia['STATUS'] == "Realizado"])
        t_validado = len(df_dia[df_dia[col_aprov_exec] == "OK"])
        t_reprovado = len(df_dia[df_dia[col_aprov_exec] == "REPROVADO"])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Aprovados p/ Hoje", t_hoje)
        m2.metric("Realizados", t_realizado)
        m3.metric("Validados", t_validado)
        m4.metric("Reprovados", t_reprovado, delta_color="inverse")

        # --- PAINEL DE VALIDAÇÃO EM MASSA ---
        if eh_gestao and not df_dia.empty:
            with st.expander("⚡ Painel de Validação em Massa (Gestão)"):
                c_m1, c_m2, c_m3, c_m4 = st.columns([1.2, 1.2, 1, 1])
                with c_m1:
                    sups = ["TODOS"] + sorted(list(df_dia['SUPERVISOR'].dropna().unique()))
                    sel_sup = st.selectbox("Supervisor:", sups, key="mass_sup")
                with c_m2:
                    v_list = df_dia[df_dia['SUPERVISOR'] == sel_sup] if sel_sup != "TODOS" else df_dia
                    vends = ["TODOS"] + sorted(list(v_list['VENDEDOR'].dropna().unique()))
                    sel_vend = st.selectbox("Vendedor:", vends, key="mass_vend")
                with c_m3:
                    acao_mass = st.radio("Ação:", ["Dar OK", "REPROVAR"], horizontal=True)
                with c_m4:
                    st.write("")
                    if st.button("🚀 EXECUTAR", use_container_width=True):
                        df_m = df_dia[df_dia['STATUS'] == "Realizado"].copy()
                        if sel_sup != "TODOS": df_m = df_m[df_m['SUPERVISOR'] == sel_sup]
                        if sel_vend != "TODOS": df_m = df_m[df_m['VENDEDOR'] == sel_vend]
                        ids_m = df_m['ID'].tolist()
                        if ids_m:
                            res = "OK" if acao_mass == "Dar OK" else "REPROVADO"
                            df_agenda.loc[df_agenda['ID'].isin(ids_m), col_aprov_exec] = res
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA'], errors='ignore'))
                            st.cache_data.clear(); st.success("Processado!"); time.sleep(1); st.rerun()

        # --- TABELA ---
        if not df_dia.empty:
            if df_base is not None:
                df_cidades = df_base[['Cliente', 'Local']].drop_duplicates(subset='Cliente').copy()
                df_dia = pd.merge(df_dia, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left')
                df_dia.rename(columns={'Local': 'CIDADE'}, inplace=True)
                df_dia = df_dia.reset_index(drop=True) # Reset após merge para segurança

            def style_audit(row):
                if row[col_aprov_exec] == "REPROVADO": return ['background-color: #FADBD8'] * len(row)
                if row[col_aprov_exec] == "OK": return ['background-color: #D4EFDF'] * len(row)
                return [''] * len(row)

            cols_v = ['EDITAR', 'VENDEDOR', 'CLIENTE', 'CIDADE', 'STATUS', 'JUSTIFICATIVA', col_aprov_exec]
            if eh_gestao: cols_v.insert(6, 'DISTANCIA_LOG')
            
            df_dia["EDITAR"] = False
            df_display = df_dia[[c for c in cols_v if c in df_dia.columns or c == "EDITAR"]].copy()

            edicao_dia = st.data_editor(
                df_display.style.apply(style_audit, axis=1),
                key="audit_dia_v2",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "EDITAR": st.column_config.CheckboxColumn("📝"),
                    "JUSTIFICATIVA": st.column_config.TextColumn("MOTIVO/JUSTIF."),
                    col_aprov_exec: st.column_config.SelectboxColumn("AUDITORIA", options=["PENDENTE", "OK", "REPROVADO"])
                },
                disabled=[c for c in df_display.columns if c not in ["EDITAR", col_aprov_exec]]
            )

            # --- EDIÇÃO INDIVIDUAL ---
            marcados = edicao_dia[edicao_dia["EDITAR"] == True]
            if not marcados.empty:
                idx = marcados.index[0]
                sel_row = df_dia.iloc[idx] # Agora o iloc funciona perfeitamente
                st.markdown("---")
                st.subheader(f"⚙️ Detalhes: {sel_row['CLIENTE']}")
                
                c1, c2, c3 = st.columns([1, 1, 1.5])
                with c1:
                    st_list = ["Planejado", "Realizado", "Reagendado"]
                    idx_st = st_list.index(sel_row['STATUS']) if sel_row['STATUS'] in st_list else 0
                    novo_status = st.selectbox("Status:", st_list, index=idx_st)
                with c2:
                    val_list = ["PENDENTE", "OK", "REPROVADO"]
                    idx_val = val_list.index(sel_row[col_aprov_exec]) if sel_row[col_aprov_exec] in val_list else 0
                    nova_val = st.radio("Validar:", val_list, index=idx_val, horizontal=True) if eh_gestao else sel_row[col_aprov_exec]
                
                with c3:
                    opcoes_just = ["", "Cliente Fechado", "Proprietário Ausente", "Sem estoque para o pedido", "Reagendado a pedido do cliente", "Visita produtiva com pedido", "Visita improdutiva", "Outros (especificar)"]
                    val_atual_just = sel_row[col_just] if pd.notna(sel_row[col_just]) else ""
                    default_idx = opcoes_just.index(val_atual_just) if val_atual_just in opcoes_just else 0
                    nova_just = st.selectbox("Escolha a Justificativa:", opcoes_just, index=default_idx)
                    if nova_just == "Outros (especificar)":
                        nova_just = st.text_input("Especifique o motivo:", value=val_atual_just if val_atual_just not in opcoes_just else "")

                if st.button("💾 SALVAR ATUALIZAÇÃO"):
                    lat_v = st.session_state.get('lat', 0)
                    lon_v = st.session_state.get('lon', 0)
                    df_agenda.loc[df_agenda['ID'] == str(sel_row['ID']), ['STATUS', col_aprov_exec, col_just, 'COORDENADAS']] = [novo_status, nova_val, nova_just, f"{lat_v}, {lon_v}"]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA'], errors='ignore'))
                    st.success("Dados atualizados!"); time.sleep(1); st.rerun()

        # --- BOTÃO ROTA FINALIZADA ---
        st.markdown("---")
        if not df_dia.empty:
            if st.button("🚩 FINALIZAR ROTA E ENVIAR RESUMO", use_container_width=True, type="primary"):
                # ... (Lógica de envio de e-mail permanece igual ao seu código original) ...
                try:
                    analista_encontrado = df_base[df_base['VENDEDOR'].str.upper() == user_atual.upper()]['ANALISTA'].iloc[0].upper().strip()
                except:
                    analista_encontrado = "NÃO LOCALIZADO"

                lista_final = EMAILS_GESTAO.copy()
                if analista_encontrado in MAPA_EMAILS:
                    lista_final.extend(MAPA_EMAILS[analista_encontrado])
                string_destinatarios = ", ".join(lista_final)

                resumo_dados = {
                    'total': len(df_dia),
                    'realizados': len(df_dia[df_dia['STATUS'] == "Realizado"]),
                    'pedidos': len(df_dia[df_dia['JUSTIFICATIVA'] == "Visita produtiva com pedido"]),
                    'pendentes': len(df_dia[df_dia['STATUS'] != "Realizado"])
                }
                taxa_conversao = (resumo_dados['pedidos'] / resumo_dados['realizados'] * 100) if resumo_dados['realizados'] > 0 else 0
                hora_finalizacao = datetime.now(fuso_br).strftime("%H:%M:%S")
                link_mapas = f"https://www.google.com/maps?q={st.session_state.get('lat', 0)},{st.session_state.get('lon', 0)}"

                with st.spinner("Enviando resumo..."):
                    sucesso = enviar_resumo_rota(
                        destinatarios_lista=string_destinatarios,
                        vendedor=user_atual,
                        dados_resumo=resumo_dados,
                        nome_analista=analista_encontrado,
                        taxa=taxa_conversao,
                        hora=hora_finalizacao,
                        link=link_mapas
                    )
                if sucesso:
                    st.success("✅ Rota finalizada e resumo enviado!")
                    #st.balloons()
                else:
                    st.error("Falha ao enviar e-mail.")
    else:
        st.info("Nenhum agendamento para hoje.")
                    
# --- PÁGINA: DASHBOARD ---
elif menu == "📊 Dashboard de Controle":
    # Cabeçalho com Botão de Atualizar
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("📊 Resumo de Engajamento por Vendedor")
    
    with col_btn:
        st.write("") 
        if st.button("🔄 Atualizar Tudo"):
            st.cache_data.clear()
            st.success("Dados Atualizados!")
            time.sleep(1)
            st.rerun()
    
    if df_base is not None and df_agenda is not None:
        # --- MAPEAMENTO DINÂMICO DE COLUNAS DA BASE ---
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'ANALISTA')
        col_sup_base = next((c for c in df_base.columns if c.upper() == 'SUPERVISOR'), 'SUPERVISOR')
        col_vend_base = next((c for c in df_base.columns if c.upper() == 'VENDEDOR'), 'VENDEDOR')
        col_cliente_base = next((c for c in df_base.columns if c.upper() == 'CLIENTE'), 'Cliente')
        col_nome_base = next((c for c in df_base.columns if c.upper() == 'NOME 1'), 'Nome 1')

        st.subheader("Filtros de Visualização")
        f_c1, f_c2, f_c3 = st.columns(3)
        df_base_filtrada = df_base.copy()
        
        with f_c1:
            if is_admin or is_diretoria:
                lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if pd.notnull(a) and str(a).strip() and str(a).lower() != 'nan'])
                ana_sel_dash = st.selectbox("Escolher Analista:", ["Todos"] + lista_analistas, key="ana_dash")
                if ana_sel_dash != "Todos":
                    df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base] == ana_sel_dash]
            else: 
                ana_sel_dash = user_atual
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base].astype(str).str.upper() == user_atual]

        with f_c2:
            lista_sups_dash = sorted([str(s) for s in df_base_filtrada[col_sup_base].unique() if pd.notnull(s) and str(s).strip() and str(s).lower() != 'nan'])
            sup_sel_dash = st.selectbox("Escolher Supervisor:", ["Todos"] + lista_sups_dash, key="sup_dash")
            if sup_sel_dash != "Todos":
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_sup_base] == sup_sel_dash]

        with f_c3:
            lista_vends_dash = sorted([str(v) for v in df_base_filtrada[col_vend_base].unique() if pd.notnull(v) and str(v).strip() and str(v).lower() != 'nan'])
            vend_sel_dash = st.selectbox("Escolher Vendedor:", ["Todos"] + lista_vends_dash, key="vend_dash")
            if vend_sel_dash != "Todos":
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_vend_base] == vend_sel_dash]

        # --- PROCESSAMENTO DE AGENDAMENTOS ---
        df_reg_agenda = df_agenda[['CÓDIGO CLIENTE', 'REGISTRO']].copy().drop_duplicates(subset='CÓDIGO CLIENTE', keep='last')
        df_base_detalhe = pd.merge(df_base_filtrada, df_reg_agenda, left_on=col_cliente_base, right_on='CÓDIGO CLIENTE', how='left')
        df_base_detalhe['STATUS AGENDAMENTO'] = df_base_detalhe['REGISTRO'].apply(lambda x: 'AGENDADO' if pd.notnull(x) and str(x).strip() != "" and str(x) != "-" else 'PENDENTE')
        df_base_detalhe['REGISTRO'] = df_base_detalhe['REGISTRO'].fillna("-")

        # --- TABELA RESUMO ---
        resumo_base = df_base_filtrada.groupby([col_ana_base, col_sup_base, col_vend_base]).size().reset_index(name='Total na Base')
        agenda_no_filtro = df_agenda[df_agenda['CÓDIGO CLIENTE'].isin(df_base_filtrada[col_cliente_base])]
        resumo_agenda = agenda_no_filtro.groupby('VENDEDOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Já Agendados')
        df_dash = pd.merge(resumo_base, resumo_agenda, left_on=col_vend_base, right_on='VENDEDOR', how='left').fillna(0)
        df_dash['Já Agendados'] = df_dash['Já Agendados'].astype(int)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Já Agendados']
        df_dash['% Conclusão'] = df_dash.apply(lambda r: f"{(r['Já Agendados']/r['Total na Base']*100):.1f}%" if r['Total na Base'] > 0 else "0.0%", axis=1)
        st.dataframe(df_dash.drop(columns=['VENDEDOR_y'], errors='ignore'), use_container_width=True, hide_index=True)

        # --- CONVERSÃO E GAPS COM AGRUPAMENTO EXATO ---
        st.markdown("---")
        st.subheader("🎯 Conversão e Gap de Mix (SKUS)")
        
        try:
            df_fat = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
            df_skus_ref = conn.read(spreadsheet=url_planilha, worksheet="SKUS")
            df_fat.columns = [str(c).strip() for c in df_fat.columns]
            df_skus_ref.columns = [str(c).strip() for c in df_skus_ref.columns]

            # --- MAPEAMENTO INTELIGENTE (CORREÇÃO DO ERRO 'DESCRIÇÃO') ---
            col_h_ref = next((c for c in df_skus_ref.columns if "HIERARQUIA" in c.upper()), "Hierarquia de produtos")
            col_sku_ref = next((c for c in df_skus_ref.columns if any(x in c.upper() for x in ["SKU", "ARTIGO"])), "SKU")
            # Busca dinâmica: Aceita DESCRIÇÃO, DESCRICAO, DESC. ou TEXTO
            col_desc_ref = next((c for c in df_skus_ref.columns if any(x in c.upper() for x in ["DESC", "TEXTO", "NOME"])), col_sku_ref)

            def agrupar_hierarquia(nome):
                n = str(nome).upper().strip()
                if n in ["DESCARTAVEIS COPOS", "DESCARTAVEIS POTES", "DESCARTAVEIS PRATOS", "DESCARTAVEIS TAMPAS"]: return "DESCARTAVEIS"
                if n in ["MILHO", "MILHO CANJICA", "MILHO CANJIQUINHA", "MILHO CREME MILHO", "MILHO FUBA"]: return "MILHO"
                if n in ["MOLHOS ALHO", "MOLHOS ALHO PICANTE"]: return "MOLHOS ALHO"
                if n in ["PIMENTA CONSERVA", "PIMENTA CONSERVA BIQUINHO", "PIMENTA CONSERVA PASTA"]: return "PIMENTA CONSERVA"
                return n

            df_skus_ref['H_AGRUPADA'] = df_skus_ref[col_h_ref].apply(agrupar_hierarquia)
            total_h_alvo = df_skus_ref['H_AGRUPADA'].nunique()
            total_s_alvo = df_skus_ref[col_sku_ref].nunique()

            col_cod_fat = df_fat.columns[10] 
            col_h_fat = next((c for c in df_fat.columns if "HIERARQUIA" in c.upper()), col_h_ref)
            col_s_fat = next((c for c in df_fat.columns if any(x in c.upper() for x in ["ARTIGO", "SKU"])), col_sku_ref)
            
            df_fat['H_AGRUPADA'] = df_fat[col_h_fat].apply(agrupar_hierarquia)
            def limpar_cod(val): return str(val).split('.')[0].strip() if pd.notnull(val) else ""
            df_fat['Cod_Limpo'] = df_fat[col_cod_fat].apply(limpar_cod)
            
            df_fat_resumo = df_fat.groupby('Cod_Limpo').agg({
                'OrdCliente': 'nunique', 'Data fat.': 'max', 'H_AGRUPADA': 'nunique', col_s_fat: 'nunique'
            }).reset_index()
            df_fat_resumo.columns = ['Cod_Cliente', 'Qtd_Pedidos', 'Ultima_Data_Fat', 'H_Vendidas', 'S_Vendidos']

            df_base_detalhe['Cliente_Limpo'] = df_base_detalhe[col_cliente_base].apply(limpar_cod)
            df_comp = pd.merge(df_base_detalhe, df_fat_resumo, left_on='Cliente_Limpo', right_on='Cod_Cliente', how='left').fillna(0)
            df_agendados_ativos = df_comp[df_comp['STATUS AGENDAMENTO'] == 'AGENDADO'].copy()
            
            # Cards de Métricas
            t_ag, v_ag = len(df_agendados_ativos), len(df_agendados_ativos[df_agendados_ativos['Qtd_Pedidos'] > 0])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Clientes Agendados", t_ag)
            c2.metric("Agendados com Venda", v_ag)
            c3.metric("Taxa de Conversão", f"{(v_ag/t_ag*100 if t_ag > 0 else 0):.1f}%")
            c4.metric("Total de Pedidos", int(df_agendados_ativos['Qtd_Pedidos'].sum()))

            with st.expander("🔍 Detalhes de GAPs e Exportação", expanded=True):
                df_conv = df_agendados_ativos[df_agendados_ativos['Qtd_Pedidos'] > 0].copy()
                df_conv['GAP FAMÍLIA'] = (total_h_alvo - df_conv['H_Vendidas']).clip(lower=0).astype(int)
                df_conv['GAP SKU'] = (total_s_alvo - df_conv['S_Vendidos']).clip(lower=0).astype(int)
                df_conv['ÚLT. FAT.'] = pd.to_datetime(df_conv['Ultima_Data_Fat'], errors='coerce').dt.strftime('%d/%m/%Y').fillna("-")
                
                df_view = df_conv[[col_cliente_base, col_nome_base, 'H_Vendidas', 'GAP FAMÍLIA', 'S_Vendidos', 'GAP SKU', 'ÚLT. FAT.']].copy()
                df_view.columns = ['CÓDIGO', 'NOME', 'FAM. ATUAIS', 'GAP FAM', 'SKU ATUAIS', 'GAP SKU', 'ÚLT. FAT.']
                df_view.insert(0, "Selecionar", False)

                edited_df = st.data_editor(df_view, use_container_width=True, hide_index=True, key="editor_gap")
                sel_cods = [str(x) for x in edited_df[edited_df['Selecionar'] == True]['CÓDIGO'].tolist()]

                # ... (dentro do if sel_cods:)
                if sel_cods:
                    output_ex = io.BytesIO()
                    
                    # Lista para consolidar os dados de todos os clientes selecionados
                    dados_consolidados = []

                    for cod in sel_cods:
                        c_l = limpar_cod(cod)
                        # Localiza info do cliente na base filtrada
                        info_cli = df_base_detalhe[df_base_detalhe['Cliente_Limpo'] == c_l].iloc[0]
                        
                        # Identifica o que ele já comprou
                        ja_comprou_cods = df_fat[df_fat['Cod_Limpo'] == c_l][col_s_fat].unique()
                        
                        # Itera sobre a referência total de SKUs para classificar cada um
                        for _, row_ref in df_skus_ref.iterrows():
                            sku_id = row_ref[col_sku_ref]
                            status = "COMPRADO" if sku_id in ja_comprou_cods else "FALTANTE"
                            
                            dados_consolidados.append({
                                "ANALISTA": info_cli[col_ana_base],
                                "SUPERVISOR": info_cli[col_sup_base],
                                "VENDEDOR": info_cli[col_vend_base],
                                "CÓD. CLIENTE": cod,
                                "CLIENTE": info_cli[col_nome_base],
                                "HIERARQUIA": row_ref['H_AGRUPADA'],
                                "SKU": sku_id,
                                "DESCRIÇÃO": row_ref[col_desc_ref],
                                "STATUS": status
                            })

                    # Cria o DataFrame final para exportação
                    df_export = pd.DataFrame(dados_consolidados)

                    # Exportação para Excel
                    with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                        df_export.to_excel(writer, sheet_name='Relatorio_Mix', index=False)
                        # Ajuste automático de colunas
                        worksheet = writer.sheets['Relatorio_Mix']
                        for i, col in enumerate(df_export.columns):
                            column_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 2
                            worksheet.set_column(i, i, column_len)

                    # --- GERAÇÃO DO PDF (Mantida como sugestão de compra rápido) ---
                    from fpdf import FPDF
                    pdf = FPDF()
                    for cod in sel_cods:
                        c_l = limpar_cod(cod)
                        info_cli = df_base_detalhe[df_base_detalhe['Cliente_Limpo'] == c_l].iloc[0]
                        pdf.add_page()
                        pdf.set_font("Arial", 'B', 12)
                        pdf.cell(0, 10, f"Sugestão de Mix - {info_cli[col_nome_base]} ({cod})", ln=True)
                        pdf.set_font("Arial", '', 8)
                        # Mostra apenas os faltantes no PDF para o vendedor focar no Gap
                        ja_comprou = df_fat[df_fat['Cod_Limpo'] == c_l][col_s_fat].unique()
                        faltantes = df_skus_ref[~df_skus_ref[col_sku_ref].isin(ja_comprou)]
                        for _, r in faltantes.head(50).iterrows():
                            pdf.cell(0, 6, f"[GAP] {r['H_AGRUPADA']} - {r[col_sku_ref]} - {str(r[col_desc_ref])[:45]}", ln=True)

                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        st.download_button("📊 Baixar Excel Consolidado", output_ex.getvalue(), "Relatorio_Mix_Completo.xlsx", "application/vnd.ms-excel")
                    with c_btn2:
                        st.download_button("📄 Baixar PDFs de Sugestão", pdf.output(dest='S').encode('latin-1', 'replace'), "Sugestao_Mix_Clientes.pdf", "application/pdf")

                st.info(f"📊 Meta do Mix: {total_h_alvo} Famílias e {total_s_alvo} SKUs únicos.")

        except Exception as e:
            st.error(f"Erro no processamento de SKUS: {e}")

       # --- NOVO BLOCO: RANKING DE ENGAJAMENTO (ACIMA DO MAPA) ---
        st.markdown("---")
        st.subheader("🏆 Ranking de Engajamento por Vendedor")
        
        # 1. Preparar dados para o Ranking
        if not df_agenda.empty:
            # Agrupar agendamentos realizados (Status = Realizado)
            ranking_realizado = df_agenda[df_agenda['STATUS'] == "Realizado"].groupby('VENDEDOR').size().reset_index(name='Realizados')
            
            # Agrupar total de agendamentos feitos
            ranking_total = df_agenda.groupby('VENDEDOR').size().reset_index(name='Total Agendado')
            
            # Unir as métricas
            df_ranking = pd.merge(ranking_total, ranking_realizado, on='VENDEDOR', how='left').fillna(0)
            df_ranking['Realizados'] = df_ranking['Realizados'].astype(int)
            
            # Calcular % de Cumprimento
            df_ranking['% Cumprimento'] = (df_ranking['Realizados'] / df_ranking['Total Agendado'] * 100).round(1)
            
            # Ordenar (quem realizou mais ganha)
            df_ranking = df_ranking.sort_values(by=['Realizados', '% Cumprimento'], ascending=False).reset_index(drop=True)
            
            # 2. Criar a coluna de Posição com Troféus
            def definir_posicao(idx):
                if idx == 0: return "🥇 1º"
                elif idx == 1: return "🥈 2º"
                elif idx == 2: return "🥉 3º"
                else: return f"{idx + 1}º"

            df_ranking.insert(0, "POS", [definir_posicao(i) for i in range(len(df_ranking))])
            
            # Exibir a Tabela de Ranking
            st.dataframe(
                df_ranking, 
                use_container_width=True, 
                hide_index=True, # Escondemos o índice original (0,1,2...)
                column_config={
                    "POS": "Posição",
                    "VENDEDOR": "Vendedor",
                    "Total Agendado": st.column_config.NumberColumn("Agendamentos"),
                    "Realizados": st.column_config.NumberColumn("Visitas Realizadas"),
                    "% Cumprimento": st.column_config.ProgressColumn("Taxa de Sucesso", format="%.1f%%", min_value=0, max_value=100)
                }
            )
        else:
            st.info("Aguardando dados de agendamento para gerar o ranking.")

        # --- MAPA DE CALOR (ABAIXO DO RANKING) ---
        st.markdown("---")
        st.subheader("🔥 Mapa de Calor")
        
        # Adicionamos uma 'key' única para evitar o erro de ID duplicado
        tipo_mapa = st.radio(
            "Selecione a camada visual:", 
            ["Visitas Realizadas", "Faturamento (Pedidos)"], 
            horizontal=True,
            key="radio_mapa_dashboard" 
        )
        
        try:
            import folium
            from folium.plugins import HeatMap
            from streamlit_folium import st_folium
            
            if tipo_mapa == "Visitas Realizadas":
                df_mapa = df_agenda[(df_agenda['STATUS'] == "Realizado") & (df_agenda['COORDENADAS'].astype(str).str.contains(',', na=False))].copy()
            else:
                # df_comp é gerado no bloco de SKUS acima
                df_mapa = df_comp[(df_comp['Qtd_Pedidos'] > 0) & (df_comp['COORDENADAS'].astype(str).str.contains(',', na=False))].copy()
            
            if not df_mapa.empty:
                # Separa latitude e longitude da coluna única COORDENADAS
                df_mapa[['lat', 'lon']] = df_mapa['COORDENADAS'].str.split(',', expand=True).astype(float)
                
                # Centraliza o mapa
                centro = [df_mapa['lat'].mean(), df_mapa['lon'].mean()]
                m = folium.Map(location=centro, zoom_start=7, tiles="cartodbpositron")
                
                # Adiciona a camada de calor
                HeatMap(df_mapa[['lat', 'lon']].dropna().values.tolist(), radius=15).add_to(m)
                
                st_folium(m, width="100%", height=500, returned_objects=[])
            else:
                st.warning("Sem dados de coordenadas para exibir no mapa com o filtro selecionado.")
                
        except Exception as e: 
            st.info(f"Aguardando dados geográficos válidos para renderizar o mapa.")
# Seria útil eu gerar um resumo de quantos clientes faltam agendar por cidade agora?
# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    
    if df_base is not None:
        # 1. MAPEAMENTO E PREPARAÇÃO DE DADOS
        col_ana_base = 'ANALISTA'
        col_sup_base = 'SUPERVISOR'
        col_ven_base = 'VENDEDOR'
        
        df_base_calc = df_base.copy()
        df_base_calc['Cliente'] = df_base_calc['Cliente'].astype(str)
        
        if df_agenda is not None and not df_agenda.empty:
            df_ag_copy = df_agenda.copy()
            df_ag_copy['CÓDIGO CLIENTE'] = df_ag_copy['CÓDIGO CLIENTE'].astype(str)
            codigos_totais_agendados = df_ag_copy[df_ag_copy['STATUS'].isin(['Planejado', 'Realizado'])]['CÓDIGO CLIENTE'].unique()
        else:
            codigos_totais_agendados = []

        # ---------------------------------------------------------
        # 2. ESPAÇO PARA OS CARDS (NO TOPO)
        # ---------------------------------------------------------
        container_cards = st.container()

        # ---------------------------------------------------------
        # 3. LÓGICA DE FILTROS (MEIO DA TELA)
        # ---------------------------------------------------------
        ven_sel = "Selecione..."
        bloqueado = False
        df_filtro_metrics = df_base_calc.copy()

        if is_admin or is_diretoria:
            lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
            ana_sel = st.selectbox("1. Filtrar por Analista:", ["Todos"] + lista_analistas)
            df_sup_f = df_base if ana_sel == "Todos" else df_base[df_base[col_ana_base] == ana_sel]
            
            lista_sups = sorted([str(s) for s in df_sup_f[col_sup_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
            sup_sel = st.selectbox("2. Filtrar por Supervisor:", ["Todos"] + lista_sups)
            df_ven_f = df_sup_f if sup_sel == "Todos" else df_sup_f[df_sup_f[col_sup_base] == sup_sel]
            
            vends = sorted([str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()])
            ven_sel = st.selectbox("3. Selecione o Vendedor:", ["Selecione..."] + vends)
            df_filtro_metrics = df_ven_f if ven_sel == "Selecione..." else df_ven_f[df_ven_f[col_ven_base] == ven_sel]

        elif is_analista:
            df_ana_f = df_base[df_base[col_ana_base].str.upper() == user_atual]
            lista_sups = sorted([str(s) for s in df_ana_f[col_sup_base].unique() if str(s).strip()])
            sup_sel = st.selectbox("1. Filtrar seu Supervisor:", ["Todos"] + lista_sups)
            df_ven_f = df_ana_f if sup_sel == "Todos" else df_ana_f[df_ana_f[col_sup_base] == sup_sel]
            vends = sorted([str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()])
            ven_sel = st.selectbox("2. Selecione o Vendedor:", ["Selecione..."] + vends)
            df_filtro_metrics = df_ven_f if ven_sel == "Selecione..." else df_ven_f[df_ven_f[col_ven_base] == ven_sel]

        elif any(df_base[col_sup_base].str.upper() == user_atual):
            df_ven_f = df_base[df_base[col_sup_base].str.upper() == user_atual]
            vends_equipe = [str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()]
            lista_final_vends = sorted(list(set(vends_equipe + [user_atual])))
            ven_sel = st.selectbox("Selecione para quem agendar:", ["Selecione..."] + lista_final_vends)
            df_filtro_metrics = df_ven_f if ven_sel == "Selecione..." else df_ven_f[df_ven_f[col_ven_base] == ven_sel]
        
        else:
            ven_sel = user_atual
            df_filtro_metrics = df_base_calc[df_base_calc[col_ven_base] == ven_sel]
            st.info(f"Sua base: {user_atual}")

        # --- CÁLCULO DAS MÉTRICAS APÓS FILTROS ---
        n_total = len(df_filtro_metrics)
        codigos_filtrados = df_filtro_metrics['Cliente'].unique()
        n_agendados = len([c for c in codigos_totais_agendados if c in codigos_filtrados])
        n_faltando = n_total - n_agendados
        perc_adesao = (n_agendados / n_total * 100) if n_total > 0 else 0

        # --- PREENCHENDO O CONTAINER DE CARDS NO TOPO ---
        with container_cards:
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Clientes na Base", n_total)
            m2.metric("Já Agendados", n_agendados)
            m3.metric("Faltando", n_faltando)
            m4.metric("% Adesão", f"{perc_adesao:.1f}%")
            st.markdown("---")

        # --- VERIFICAÇÃO DE PUNIÇÃO ---
        if ven_sel != "Selecione...":
            hoje_dt = datetime.now(fuso_br).date()
            df_verif = df_agenda[df_agenda['VENDEDOR'].str.upper() == ven_sel.upper()].copy()
            if not df_verif.empty:
                df_verif['DT_OBJ'] = pd.to_datetime(df_verif['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                pendencias_passadas = df_verif[(df_verif['DT_OBJ'] < hoje_dt) & (df_verif['STATUS'] == "Planejado")]
                if not pendencias_passadas.empty:
                    bloqueado = True
                    st.error(f"⚠️ **AGENDAMENTO BLOQUEADO PARA {ven_sel}**")
                    with st.expander("Ver visitas pendentes"):
                        st.table(pendencias_passadas[['DATA', 'CLIENTE', 'STATUS']].sort_values(by='DATA'))

        # --- FORMULÁRIO DE AGENDAMENTO (SALVAMENTO RESTAURADO) ---
        if ven_sel != "Selecione..." and not bloqueado:
            clientes_pendentes = df_filtro_metrics[~df_filtro_metrics['Cliente'].isin(codigos_totais_agendados)]
            
            try:
                amostra = df_filtro_metrics.iloc[0]
                analista_vinc = str(amostra[col_ana_base]).upper()
                supervisor_vinc = str(amostra[col_sup_base]).upper()
            except:
                analista_vinc = "N/I"; supervisor_vinc = "N/I"

            lista_c = sorted(clientes_pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            
            if not lista_c:
                st.success(f"✅ Todos os clientes de {ven_sel} já foram agendados!")
            else:
                cliente_sel = st.selectbox("Selecione o Cliente para Agendar:", ["Selecione..."] + lista_c)
                if cliente_sel != "Selecione...":
                    qtd_visitas = st.number_input("Quantidade de visitas:", min_value=1, max_value=4, value=1)
                    
                    with st.form("form_novo_v", clear_on_submit=True):
                        cols_datas = st.columns(qtd_visitas)
                        hoje_dt = datetime.now(fuso_br).date()
                        datas_sel = [cols_datas[i].date_input(f"Data {i+1}:", value=hoje_dt, min_value=hoje_dt, key=f"d_{i}") for i in range(qtd_visitas)]
                        
                        if st.form_submit_button("💾 SALVAR AGENDAMENTOS"):
                            cod_c, nom_c = cliente_sel.split(" - ", 1)
                            agora = datetime.now(fuso_br)
                            novas_linhas = []
                            
                            for i, dt in enumerate(datas_sel):
                                nid = agora.strftime("%Y%m%d%H%M%S") + str(i)
                                novas_linhas.append({
                                    "ID": nid, 
                                    "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), 
                                    "DATA": dt.strftime("%d/%m/%Y"), 
                                    "ANALISTA": analista_vinc, 
                                    "SUPERVISOR": supervisor_vinc, 
                                    "VENDEDOR": ven_sel,
                                    "CÓDIGO CLIENTE": str(cod_c), 
                                    "CLIENTE": nom_c, 
                                    "JUSTIFICATIVA": "-", 
                                    "STATUS": "Planejado", 
                                    "AGENDADO POR": user_atual 
                                })
                            
                            # Concatenar e atualizar a planilha
                            df_final_a = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas_linhas)], ignore_index=True)
                            df_final_a = df_final_a.drop_duplicates(subset=['VENDEDOR', 'CÓDIGO CLIENTE', 'DATA'], keep='first')
                            
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                            st.cache_data.clear()
                            st.success("✅ Agendamento Realizado com Sucesso!")
                            time.sleep(1)
                            st.rerun()
# --- PÁGINA: VER/EDITAR ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("🔍 Minha Agenda Completa")
    
    with col_btn:
        if st.button("🔄 Atualizar Dados", key="btn_refresh_agenda"):
            st.cache_data.clear()
            st.rerun()
    
    if df_agenda is not None and not df_agenda.empty:
        # --- 1. LIMPEZA DE DUPLICADOS E RESET DE ÍNDICE ---
        df_agenda = df_agenda.drop_duplicates(
            subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'], 
            keep='first'
        ).reset_index(drop=True)
        
        # Garantir que colunas essenciais existam
        colunas_necessarias = ['APROVACAO', 'OBS_GESTAO', 'ANALISTA', 'SUPERVISOR', 'VENDEDOR', 'DISTANCIA_LOG']
        for col in colunas_necessarias:
            if col not in df_agenda.columns:
                df_agenda[col] = 0 if col == 'DISTANCIA_LOG' else ""

        # Padronização de valores vazios
        df_agenda['APROVACAO'] = df_agenda['APROVACAO'].fillna("Pendente").replace(["", "none", "None", "nan", "NaN"], "Pendente")

        # --- 2. PREPARAÇÃO DE DATAS ---
        df_agenda['DT_COMPLETA'] = pd.to_datetime(df_agenda['DATA'], dayfirst=True, errors='coerce')

        # --- 3. LÓGICA DE FILTRO POR HIERARQUIA ---
        if is_admin or is_diretoria:
            df_user = df_agenda.copy()
            st.info("💡 Visão de Administrador: Todos os registros exibidos.")
        elif is_analista:
            df_user = df_agenda[df_agenda['ANALISTA'].astype(str).str.upper() == user_atual.upper()].copy()
        elif is_supervisor:
            df_user = df_agenda[df_agenda['SUPERVISOR'].astype(str).str.upper() == user_atual.upper()].copy()
        else:
            df_user = df_agenda[df_agenda['VENDEDOR'].astype(str).str.upper() == user_atual.upper()].copy()

        df_user = df_user.reset_index(drop=True)

        if not df_user.empty:
            # --- 4. FILTROS DINÂMICOS ---
            with st.expander("🎯 Filtros de Visualização", expanded=False):
                f_col1, f_col2, f_col3 = st.columns(3)
                def get_options(df, col):
                    return ["Todos"] + sorted([str(x) for x in df[col].unique() if x and str(x).lower() != 'nan'])

                ana_f = f_col1.selectbox("Filtrar Analista:", get_options(df_user, 'ANALISTA'))
                df_temp = df_user if ana_f == "Todos" else df_user[df_user['ANALISTA'] == ana_f]
                
                sup_f = f_col2.selectbox("Filtrar Supervisor:", get_options(df_temp, 'SUPERVISOR'))
                df_temp = df_temp if sup_f == "Todos" else df_temp[df_temp['SUPERVISOR'] == sup_f]
                
                vend_f = f_col3.selectbox("Filtrar Vendedor:", get_options(df_temp, 'VENDEDOR'))
                
                if ana_f != "Todos": df_user = df_user[df_user['ANALISTA'] == ana_f]
                if sup_f != "Todos": df_user = df_user[df_user['SUPERVISOR'] == sup_f]
                if vend_f != "Todos": df_user = df_user[df_user['VENDEDOR'] == vend_f]
                df_user = df_user.reset_index(drop=True)

            # --- 5. MÉTRICAS ---
            m1, m2, m3 = st.columns(3)
            m1.metric("📅 Total Agendado", len(df_user))
            m2.metric("⏳ Total Pendente", len(df_user[df_user['STATUS'] == "Planejado"]))
            m3.metric("✅ Total Realizado", len(df_user[df_user['STATUS'] == "Realizado"]))
            st.markdown("---")

            # --- 6. APROVAÇÃO EM MASSA (GESTÃO) ---
            if (is_admin or is_diretoria or is_analista):
                with st.expander("⚖️ Painel de Aprovação de Agendas", expanded=False):
                    col_ap1, col_ap2, col_ap3 = st.columns([2, 2, 3])
                    vends_na_lista = sorted([str(x) for x in df_user['VENDEDOR'].unique() if x])
                    vend_alvo = col_ap1.selectbox("Vendedor:", ["Todos"] + vends_na_lista, key="sel_massa_v")
                    status_massa = col_ap2.selectbox("Definir:", ["Aprovado", "Reprovado"], key="sel_massa_s")
                    obs_massa = col_ap3.text_input("Observação:", key="obs_massa_input")
                    
                    if st.button("🚀 Aplicar Decisão em Massa"):
                        mask = df_agenda['VENDEDOR'] == vend_alvo if vend_alvo != "Todos" else df_agenda['VENDEDOR'].isin(vends_na_lista)
                        df_agenda.loc[mask, 'APROVACAO'] = status_massa
                        df_agenda.loc[mask, 'OBS_GESTAO'] = obs_massa
                        if status_massa == "Reprovado":
                            df_agenda.loc[mask, 'STATUS'] = "Reprovado"
                        
                        df_save = df_agenda.drop_duplicates(subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'])
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save.drop(columns=['LINHA', 'DT_COMPLETA'], errors='ignore'))
                        st.cache_data.clear(); st.success("Atualizado!"); time.sleep(1); st.rerun()

            # --- 7. TABELA COM ANALISTA E DISTÂNCIA ---
            df_user["AÇÃO"] = False
            
            # Definindo as colunas para exibição (Incluindo Analista e Distância)
            cols_display = ['AÇÃO', 'DATA', 'ANALISTA', 'VENDEDOR', 'CLIENTE', 'STATUS', 'APROVACAO', 'DISTANCIA_LOG', 'OBS_GESTAO']
            
            # Filtra apenas as colunas que realmente existem no DF para evitar erro
            df_display = df_user[[c for c in cols_display if c in df_user.columns or c == "AÇÃO"]].copy()

            edicao_user = st.data_editor(
                df_display, 
                key="edit_agenda_final_v3", 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "AÇÃO": st.column_config.CheckboxColumn("📌"),
                    "DISTANCIA_LOG": st.column_config.NumberColumn("Distância (m)", format="%d m"),
                    "DATA": st.column_config.TextColumn("Data"),
                    "ANALISTA": st.column_config.TextColumn("Analista")
                },
                disabled=[c for c in df_display.columns if c != "AÇÃO"]
            )
            
            # --- 8. GERENCIAMENTO INDIVIDUAL ---
            marcados = edicao_user[edicao_user["AÇÃO"] == True]
            if not marcados.empty:
                idx_selecionado = marcados.index[0]
                sel_row = df_user.iloc[idx_selecionado]
                
                st.markdown(f"### ⚙️ Gerenciar: {sel_row['CLIENTE']}")
                t1, t2, t3 = st.tabs(["⚖️ Aprovação", "🔄 Reagendar", "🗑️ Excluir"])
                
                with t1:
                    if is_admin or is_diretoria or is_analista:
                        col_ind1, col_ind2 = st.columns(2)
                        n_status = col_ind1.selectbox("Decisão:", ["Aprovado", "Reprovado"], key="n_status_ind")
                        n_obs = col_ind2.text_input("Motivo:", value=str(sel_row['OBS_GESTAO']), key="n_obs_ind")
                        
                        if st.button("Salvar Decisão Individual"):
                            df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['APROVACAO', 'OBS_GESTAO']] = [n_status, n_obs]
                            if n_status == "Reprovado":
                                df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Reprovado"
                            
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                            st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()
                    else:
                        st.warning("Apenas gestores podem alterar a aprovação.")

                with t2:
                    n_data = st.date_input("Nova Data:", value=datetime.now(), key="date_reag")
                    if st.button("Confirmar Reagendamento"):
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['DATA', 'STATUS', 'APROVACAO']] = [n_data.strftime('%d/%m/%Y'), "Planejado", "Pendente"]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                        st.cache_data.clear(); st.success("Reagendado!"); time.sleep(1); st.rerun()
                
                with t3:
                    st.error("Atenção: Esta ação excluirá o registro permanentemente.")
                    if st.button("🗑️ CONFIRMAR EXCLUSÃO"):
                        df_agenda = df_agenda[df_agenda['ID'] != sel_row['ID']]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                        st.cache_data.clear(); st.success("Excluído"); time.sleep(1); st.rerun()
        else:
            st.info("Nenhum agendamento encontrado para os filtros selecionados.")
# --- PÁGINA: DESEMPENHO DE VENDAS (FATURADO) 
elif menu_interna == "📊 Desempenho de Vendas":
    st.header("📊 Desempenho de Vendas (Faturado)")
    
    try:
        # 1. Leitura das abas
        df_faturado = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
        df_metas_cob = conn.read(spreadsheet=url_planilha, worksheet="META COBXPOSIT")
        df_param_metas = conn.read(spreadsheet=url_planilha, worksheet="PARAM_METAS")
        df_meta_sistema = conn.read(spreadsheet=url_planilha, worksheet="META SISTEMA")
        df_2025 = conn.read(spreadsheet=url_planilha, worksheet="META 2025")
        
        lista_hierarquia_fixa = [
            "ACHOCOLATADO", "ACUCAR", "ADOCANTE SACARINA", "ADOCANTE SUCRALOSE", "AZEITONA", 
            "BALSAMICO", "BEBIDA MISTA", "CALDOS TABLETE", "CATCHUP", "CEBOLINHA", "COGUMELO", 
            "DESCARTAVEIS", "ESPECIARIAS", "FARINHA DE TRIGO FD", "FARINHA DE TRIGO SC", 
            "FARINHA LACTEA", "MACARRAO INSTANTANEO", "MARATINHO", "MILHO", "MILHO FARINHA GOTA", 
            "MILHO FARINHA MARATA", "MILHO FLOCAO GOTA", "MILHO FLOCAO MARATA", "MILHO PIPOCA", 
            "MINGAU", "MISTURA BOLO", "MOLHO PRONTO", "MOLHOS ALHO", "MOLHOS INGLES", 
            "MOLHOS LIMAO", "MOLHOS PIMENTA", "MOLHOS PIMENTA 75ML", "MOLHOS SALSA", 
            "MOLHOS SHOYO", "MOLHOS TEMPEROS CASEIROS", "OLEAGINOSAS", "PIMENTA CONSERVA", 
            "PIPOCA PRONTA", "REFRESCO", "SALGADINHOS FARDO", "SALGADINHOS NACHOS", 
            "SALGADINHOS PASTEIS", "SUCO D+ 1000ML", "SUCO D+ 200ML", "SUCO MARATA 1000ML", 
            "SUCO MARATA 200ML", "TEMPERO COLORIFICO GOTA", "TEMPERO COLORIFICO MARATA", 
            "TEMPERO CONDIMENTO GOTA", "TEMPERO CONDIMENTO MARATA", "TEMPERO EM PO", 
            "VINAGRE", "VINAGRE ESPECIAL"
        ]

        # Tratamento das Metas
        if df_meta_sistema is not None:
            df_meta_sistema.columns = [str(c).strip() for c in df_meta_sistema.columns]
            df_meta_sistema['RG'] = df_meta_sistema['RG'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_meta_sistema['QTD'] = pd.to_numeric(df_meta_sistema['QTD'], errors='coerce').fillna(0)
            if 'HIERARQUIA DE PRODUTOS' in df_meta_sistema.columns:
                df_meta_sistema['HIERARQUIA DE PRODUTOS'] = df_meta_sistema['HIERARQUIA DE PRODUTOS'].astype(str).str.strip().str.upper()

        if df_2025 is not None:
            df_2025.columns = [str(c).strip() for c in df_2025.columns]
            df_2025['RG'] = df_2025['RG'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_2025['QUANTIDADE'] = pd.to_numeric(df_2025['QUANTIDADE'], errors='coerce').fillna(0)
            if 'HIERARQUIA DE PRODUTOS' in df_2025.columns:
                df_2025['HIERARQUIA DE PRODUTOS'] = df_2025['HIERARQUIA DE PRODUTOS'].astype(str).str.strip().str.upper()

        if df_faturado is not None and not df_faturado.empty:
            df_faturado = df_faturado.dropna(how='all')
            df_faturado.columns = [str(c).strip() for c in df_faturado.columns]
            df_faturado.rename(columns={'Região de vendas': 'VENDEDOR_NOME','RG': 'VENDEDOR_COD','Qtd Vendas (S/Dec)': 'QTD_VENDAS','Hierarquia de produtos': 'HIERARQUIA'}, inplace=True)
            df_faturado['QTD_VENDAS'] = pd.to_numeric(df_faturado['QTD_VENDAS'], errors='coerce').fillna(0)
            df_faturado['VENDEDOR_COD'] = df_faturado['VENDEDOR_COD'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            def aplicar_agrupamento_custom(item):
                item = str(item).strip().upper()
                mapeamento = {'DESCARTAVEIS COPOS': 'DESCARTAVEIS', 'DESCARTAVEIS PRATOS': 'DESCARTAVEIS', 'DESCARTAVEIS TAMPAS': 'DESCARTAVEIS', 'DESCARTAVEIS POTES': 'DESCARTAVEIS','MILHO CANJICA': 'MILHO', 'MILHO CANJIQUINHA': 'MILHO','MILHO CREME MILHO': 'MILHO', 'MILHO FUBA': 'MILHO','MOLHOS ALHO PICANTE': 'MOLHOS ALHO','PIMENTA CONSERVA BIQUINHO': 'PIMENTA CONSERVA','PIMENTA CONSERVA PASTA': 'PIMENTA CONSERVA'}
                return mapeamento.get(item, item)
            
            df_faturado['HIERARQUIA'] = df_faturado['HIERARQUIA'].apply(aplicar_agrupamento_custom)
            df_relacao = df_base[['VENDEDOR', 'SUPERVISOR', 'ANALISTA']].drop_duplicates(subset=['VENDEDOR'])
            df_faturado = pd.merge(df_faturado, df_relacao, left_on='VENDEDOR_NOME', right_on='VENDEDOR', how='left')
            col_k = 'K' if 'K' in df_faturado.columns else df_faturado.columns[10]

        if df_param_metas is not None:
            df_param_metas.columns = [str(c).strip() for c in df_param_metas.columns]
            df_param_metas['BASE'] = pd.to_numeric(df_param_metas['BASE'], errors='coerce').fillna(0)
            metas_raw = pd.to_numeric(df_param_metas['META_COB'].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce').fillna(0)
            df_param_metas['META_COB'] = metas_raw.apply(lambda x: x * 100 if x > 0 and x <= 1.0 else x)
            df_param_metas['EscrV'] = df_param_metas['EscrV'].astype(str).str.strip()

        if df_metas_cob is not None:
            df_metas_cob.columns = [str(c).strip() for c in df_metas_cob.columns]
            df_metas_cob['RG'] = df_metas_cob['RG'].astype(str).str.strip()
            df_metas_cob['BASE'] = pd.to_numeric(df_metas_cob['BASE'], errors='coerce').fillna(0)
            metas_vend_raw = pd.to_numeric(df_metas_cob['META'].astype(str).str.replace('%','').str.replace(',','.'), errors='coerce').fillna(0)
            df_metas_cob['META'] = metas_vend_raw.apply(lambda x: x * 100 if x > 0 and x <= 1.0 else x)

    except Exception as e:
        st.error(f"Erro no processamento das abas: {e}")
        st.stop()

    if df_faturado is not None and not df_faturado.empty:
        df_f = df_faturado.copy()
        df_ms = df_meta_sistema.copy() if df_meta_sistema is not None else None
        df_25 = df_2025.copy() if df_2025 is not None else None
        
        st.markdown("### 🔍 Filtros")
        c0, c2, c3 = st.columns(3)
        with c0: sel_estado = st.multiselect("Estado", sorted(df_f['EscrV'].dropna().unique()))
        with c2: 
            df_temp_sup = df_f[df_f['EscrV'].isin(sel_estado)] if sel_estado else df_f
            sel_supervisor = st.multiselect("Supervisor", sorted(df_temp_sup['SUPERVISOR'].dropna().unique()))
        with c3:
            df_temp_vend = df_temp_sup[df_temp_sup['SUPERVISOR'].isin(sel_supervisor)] if sel_supervisor else df_temp_sup
            sel_vendedor = st.multiselect("Vendedor", sorted(df_temp_vend['VENDEDOR_NOME'].dropna().unique()))

        if sel_estado: df_f = df_f[df_f['EscrV'].isin(sel_estado)]
        if sel_supervisor: df_f = df_f[df_f['SUPERVISOR'].isin(sel_supervisor)]
        if sel_vendedor: df_f = df_f[df_f['VENDEDOR_NOME'].isin(sel_vendedor)]
            
        vendedores_ids = df_f['VENDEDOR_COD'].unique()
        if df_ms is not None: df_ms = df_ms[df_ms['RG'].isin(vendedores_ids)]
        if df_25 is not None: df_25 = df_25[df_25['RG'].isin(vendedores_ids)]

        if not df_f.empty:
            if not (sel_supervisor or sel_vendedor):
                df_limpo = df_f[~df_f['EqVs'].astype(str).str.contains('SMX|STR', na=False)] if 'EqVs' in df_f.columns else df_f
                positivacao = df_limpo[col_k].nunique()
                dados_meta = df_param_metas[df_param_metas['EscrV'].isin(df_f['EscrV'].unique())]
                base_total = dados_meta['BASE'].sum() if not dados_meta.empty else 1
                meta_val = dados_meta['META_COB'].mean() if not dados_meta.empty else 0
            else:
                positivacao = df_f[col_k].nunique()
                dados_meta = df_metas_cob[df_metas_cob['RG'].isin([str(x) for x in vendedores_ids])]
                base_total = dados_meta['BASE'].sum() if not dados_meta.empty else 1
                meta_val = dados_meta['META'].mean() if not dados_meta.empty else 0
            
            real_perc = (positivacao / base_total * 100) if base_total > 0 else 0
            cor_indicador = "#28a745" if real_perc >= meta_val else "#e67e22"

        # --- PREPARAÇÃO DOS DADOS (PROCESSA UMA VEZ SÓ) ---
        df_f_agrupado = df_f.groupby('HIERARQUIA').agg({'QTD_VENDAS': 'sum', col_k: 'nunique'}).rename(columns={'QTD_VENDAS': 'VOLUME', col_k: 'POSITIVADO_REAL'}).reset_index()
        df_ms_agrupado = df_ms.groupby('HIERARQUIA DE PRODUTOS')['QTD'].sum().reset_index().rename(columns={'HIERARQUIA DE PRODUTOS': 'HIERARQUIA', 'QTD': 'META 2026'}) if df_ms is not None else pd.DataFrame(columns=['HIERARQUIA', 'META 2026'])
        df_25_agrupado = df_25.groupby('HIERARQUIA DE PRODUTOS')['QUANTIDADE'].sum().reset_index().rename(columns={'HIERARQUIA DE PRODUTOS': 'HIERARQUIA', 'QUANTIDADE': 'META 2025'}) if df_25 is not None else pd.DataFrame(columns=['HIERARQUIA', 'META 2025'])
        df_metas_sub = df_metas_cob[df_metas_cob['EscrV'].isin(df_f['EscrV'].unique())] if not df_f.empty else df_metas_cob
        df_metas_hierarquia = df_metas_sub.groupby('HIERARQUIA DE PRODUTOS')['META COBERTURA'].mean().reset_index().rename(columns={'HIERARQUIA DE PRODUTOS': 'HIERARQUIA'}) if 'META COBERTURA' in df_metas_sub.columns else pd.DataFrame(columns=['HIERARQUIA', 'META COBERTURA'])

        df_final_h = pd.merge(pd.DataFrame(lista_hierarquia_fixa, columns=['HIERARQUIA']), df_f_agrupado, on='HIERARQUIA', how='left')
        df_final_h = pd.merge(df_final_h, df_metas_hierarquia, on='HIERARQUIA', how='left')
        df_final_h = pd.merge(df_final_h, df_25_agrupado, on='HIERARQUIA', how='left') 
        df_final_h = pd.merge(df_final_h, df_ms_agrupado, on='HIERARQUIA', how='left').fillna(0)
        
        df_final_h['META CLIENTES (ABS)'] = (df_final_h['META COBERTURA'] / 100) * base_total
        df_final_h = df_final_h.rename(columns={'HIERARQUIA': 'HIERARQUIA DE PRODUTOS', 'POSITIVADO_REAL': 'POSITIVAÇÃO'})
        df_final_h['PENDÊNCIA CLIENTES'] = (df_final_h['META CLIENTES (ABS)'] - df_final_h['POSITIVAÇÃO']).clip(lower=0)
        df_final_h['CRESCIMENTO 2025'] = df_final_h['VOLUME'] - df_final_h['META 2025']
        df_final_h['ATINGIMENTO % (VOL 2025)'] = (df_final_h['VOLUME'] / df_final_h['META 2025'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        df_final_h['CRESCIMENTO 2026'] = df_final_h['VOLUME'] - df_final_h['META 2026']
        df_final_h['ATINGIMENTO % (VOL 2026)'] = (df_final_h['VOLUME'] / df_final_h['META 2026'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)

        # --- ÁREA VISUAL: RESUMO ---
        st.markdown("---")
        
        qtd_total_itens = len(df_final_h)
        itens_atingiram = len(df_final_h[df_final_h['VOLUME'] >= df_final_h['META 2025']])
        itens_abaixo = qtd_total_itens - itens_atingiram
        meta_fixa_perc = 80
        realizado_perc_resumo = (itens_atingiram / qtd_total_itens * 100) if qtd_total_itens > 0 else 0
        falta_perc = max(0, meta_fixa_perc - realizado_perc_resumo)

        col_res, col_cob = st.columns([1.5, 1])

        with col_res:
            st.markdown(f"""
                <table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px;">
                    <tr style="background-color: #0070C0; color: white; font-weight: bold; text-align: center;">
                        <td colspan="2" style="padding: 8px; border: 1px solid #dee2e6;">RESUMO DE CRESCIMENTO (Vs META 2025)</td>
                    </tr>
                    <tr><td style="padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;">QUANTOS ITENS TEM NO TOTAL</td><td style="padding: 5px; border: 1px solid #dee2e6; text-align: center; font-weight: bold;">{qtd_total_itens}</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;">ITENS QUE ATINGIRAM</td><td style="padding: 5px; border: 1px solid #dee2e6; text-align: center; font-weight: bold; color: green;">{itens_atingiram}</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;">ITENS ABAIXO DA META</td><td style="padding: 5px; border: 1px solid #dee2e6; text-align: center; font-weight: bold; color: red;">{itens_abaixo}</td></tr>
                    <tr style="background-color: #E7E6E6;"><td style="padding: 5px; border: 1px solid #dee2e6;">META FIXA</td><td style="padding: 5px; border: 1px solid #dee2e6; text-align: center; font-weight: bold;">{meta_fixa_perc}%</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;">REALIZADO (%)</td><td style="padding: 5px; border: 1px solid #dee2e6; text-align: center; font-weight: bold; color: {'green' if realizado_perc_resumo >= meta_fixa_perc else '#e67e22'};">{realizado_perc_resumo:.1f}%</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #dee2e6; background-color: #f8f9fa;">QUANTO FALTA (%)</td><td style="padding: 5px; border: 1px solid #dee2e6; text-align: center; font-weight: bold; color: red;">{falta_perc:.1f}%</td></tr>
                </table>
            """, unsafe_allow_html=True)

        with col_cob:
            base_fmt = f"{base_total:,.0f}".replace(",", ".")
            atingido_fmt = f"{real_perc:.1f}".replace(".", ",") + "%"
            st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 18px; border-radius: 8px; background-color: #f9f9f9; height: 100%;">
                    <small style="color: #666;">COBERTURA</small><br>
                    <span style="font-size: 1.1em;">Base: <b>{base_fmt}</b> | Meta: <b>{meta_val:.0f}%</b></span><br>
                    Atingido: <span style="color:{cor_indicador}; font-size: 1.8em; font-weight: bold;">{atingido_fmt}</span>
                </div>
            """, unsafe_allow_html=True)

        # --- EXIBIÇÃO DA TABELA DETALHADA (APENAS UMA VEZ) ---
        st.markdown("### 📈 Desempenho por Hierarquia")
        
        colunas_ordenadas = [
            'HIERARQUIA DE PRODUTOS', 'META COBERTURA', 'META CLIENTES (ABS)', 'POSITIVAÇÃO', 
            'PENDÊNCIA CLIENTES', 'META 2025', 'META 2026', 'VOLUME', 
            'CRESCIMENTO 2025', 'ATINGIMENTO % (VOL 2025)', 'CRESCIMENTO 2026', 'ATINGIMENTO % (VOL 2026)'
        ]
        df_final_h = df_final_h[colunas_ordenadas]

        def aplicar_estilo(val):
            if isinstance(val, (int, float)) and val < 0: return 'color: #d63031; font-weight: bold;'
            return ''

        st.dataframe(
            df_final_h.sort_values(by=['HIERARQUIA DE PRODUTOS'], ascending=True).style
            .format({
                'META COBERTURA': "{:.1f}%",
                'META CLIENTES (ABS)': lambda x: f"{x:,.0f}".replace(",", "."),
                'POSITIVAÇÃO': lambda x: f"{x:,.0f}".replace(",", "."),
                'PENDÊNCIA CLIENTES': lambda x: f"{x:,.0f}".replace(",", "."),
                'META 2025': lambda x: f"{x:,.0f}".replace(",", "."),
                'META 2026': lambda x: f"{x:,.0f}".replace(",", "."),
                'VOLUME': lambda x: f"{x:,.0f}".replace(",", "."),
                'CRESCIMENTO 2025': lambda x: f"{x:,.0f}".replace(",", "."),
                'CRESCIMENTO 2026': lambda x: f"{x:,.0f}".replace(",", "."),
                'ATINGIMENTO % (VOL 2025)': "{:.1f}%",
                'ATINGIMENTO % (VOL 2026)': "{:.1f}%"
            })
            .applymap(aplicar_estilo, subset=['CRESCIMENTO 2025', 'CRESCIMENTO 2026'])
            .bar(subset=['ATINGIMENTO % (VOL 2025)', 'ATINGIMENTO % (VOL 2026)'], color=['#ffadad', '#72efdd'], align='mid', vmin=0, vmax=100)
            .apply(lambda x: ['background-color: #fff3cd' if (v > 0) else '' for v in x], subset=['PENDÊNCIA CLIENTES']),
            use_container_width=True,
            hide_index=True
        )
        # --- ÁREA DE EXPORTAÇÃO ---
        st.markdown("### 📥 Exportar Relatório")
        col_btn1, col_btn2, _ = st.columns([1, 1, 2])

        # --- PREPARAÇÃO DOS FILTROS PARA O EXCEL ---
        # Criamos um pequeno DataFrame com o resumo dos filtros selecionados
        filtros_selecionados = {
            "Filtro": ["Estado", "Supervisor", "Vendedor"],
            "Valores": [
                ", ".join(sel_estado) if sel_estado else "Todos",
                ", ".join(sel_supervisor) if sel_supervisor else "Todos",
                ", ".join(sel_vendedor) if sel_vendedor else "Todos"
            ]
        }
        df_filtros = pd.DataFrame(filtros_selecionados)

        # --- FUNÇÃO EXCEL ---
        buffer_excel = io.BytesIO()
        df_excel = df_final_h.copy()

        # Ajuste de porcentagem para o Excel
        cols_pct = ['META COBERTURA', 'ATINGIMENTO % (VOL 2025)', 'ATINGIMENTO % (VOL 2026)']
        for col in cols_pct:
            df_excel[col] = df_excel[col] / 100

        with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
            # 1. Planilha Principal
            df_excel.to_excel(writer, index=False, sheet_name='Desempenho')
            
            # 2. Planilha de Filtros (O que foi selecionado nos Slicers)
            df_filtros.to_excel(writer, index=False, sheet_name='Filtros Aplicados')
            
            workbook  = writer.book
            worksheet = writer.sheets['Desempenho']
            ws_filtros = writer.sheets['Filtros Aplicados']

            # Formatos
            format_pct = workbook.add_format({'num_format': '0.0%', 'align': 'center'})
            format_num = workbook.add_format({'num_format': '#,##0', 'align': 'right'})
            format_header = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})

            # Aplicar formatos na aba principal
            worksheet.set_column(1, 1, 15, format_pct)  # Meta Cob
            worksheet.set_column(2, 7, 15, format_num)  # Valores
            worksheet.set_column(9, 9, 20, format_pct)  # Atig 25
            worksheet.set_column(11, 11, 20, format_pct) # Atig 26
            worksheet.set_column(8, 8, 15, format_num)  # Cresc 25
            worksheet.set_column(10, 10, 15, format_num) # Cresc 26
            
            # Estilizar aba de filtros para ficar organizado
            ws_filtros.set_column(0, 0, 20, format_header)
            ws_filtros.set_column(1, 1, 60)

        with col_btn1:
            st.download_button(
                label="📊 Baixar Excel",
                data=buffer_excel.getvalue(),
                file_name="relatorio_desempenho.xlsx",
                mime="application/vnd.ms-excel"
            )

        # --- FUNÇÃO PDF (ADICIONANDO FILTROS NO TOPO) ---
        def generate_pdf(data):
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            
            # Título
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Relatorio de Desempenho de Vendas", ln=True, align='C')
            
            # Informações dos Filtros no PDF
            pdf.set_font("Arial", 'I', 8)
            texto_filtros = f"Filtros - Estado: {filtros_selecionados['Valores'][0]} | " \
                            f"Supervisor: {filtros_selecionados['Valores'][1]} | " \
                            f"Vendedor: {filtros_selecionados['Valores'][2]}"
            pdf.cell(0, 8, texto_filtros, ln=True, align='L')
            pdf.ln(2)
            
            # Tabela
            pdf.set_font("Arial", size=7)
            cols = data.columns.tolist()
            for col in cols:
                pdf.cell(23, 8, str(col)[:14], border=1, align='C')
            pdf.ln()
            
            for _, row in data.iterrows():
                for col in cols:
                    val = row[col]
                    if col in cols_pct:
                        txt = f"{val:.1f}%".replace(".", ",")
                    elif isinstance(val, (int, float)):
                        txt = f"{val:,.0f}".replace(",", ".")
                    else:
                        txt = str(val)
                    pdf.cell(23, 7, txt, border=1, align='R')
                pdf.ln()
            
            return pdf.output(dest='S').encode('latin-1')

        with col_btn2:
            try:
                pdf_bytes = generate_pdf(df_final_h)
                st.download_button(
                    label="📄 Baixar PDF",
                    data=pdf_bytes,
                    file_name="relatorio_desempenho.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.warning(f"Erro ao gerar PDF: {e}")
