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
    "BARBARA": ["barbara.costa@marata.com.br", "kaio.gomes@marata.com.br"],
    "THAIS": ["thais.oliveira@marata.com.br"],
    "REGIANE": ["regiane.santana@marata.com.br"],
    "ALLANA": ["allana.menezes@marata.com.br", "danilo.matos@marata.com.br"],
    "ROBERIO": ["roberio@marata.com.br", "dione.lima@marata.com.br"]
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
        msg['From'] = email_origem
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

    # ADICIONADO: "📊 Desempenho de Vendas" disponível para todos
    opcoes_menu = ["📅 Agendamentos do Dia", "📋 Novo Agendamento", texto_ver_agenda, "📊 Desempenho de Vendas"]
    
    if eh_gestao:
        opcoes_menu.append("📊 Dashboard de Controle")
        
    menu = st.selectbox("Menu Principal", opcoes_menu)
    
    # Padronização interna para o código
    if menu == texto_ver_agenda:
        menu_interna = "🔍 Ver/Editar Minha Agenda"
    else:
        menu_interna = menu # Aqui ele já vai aceitar "📊 Desempenho de Vendas"

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
            lista_sups_limpar = sorted(df_agenda['SUPERVISOR'].unique())
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups_limpar, key="sel_limpeza_admin")

            if sup_limpar != "Selecione...":
                confirma = st.popover(f"⚠️ APAGAR: {sup_limpar}")
                if confirma.button(f"Confirmar Exclusão de {sup_limpar}", key="btn_conf_limpeza"):
                    df_rest = df_agenda[df_agenda['SUPERVISOR'] != sup_limpar].drop(columns=['LINHA'], errors='ignore')
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                    st.cache_data.clear()
                    st.success("Agenda limpa!"); time.sleep(1); st.rerun()

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
        if st.button("🔄 Atualizar Agenda"):
            st.cache_data.clear()
            st.rerun()

    hoje_str = datetime.now(fuso_br).strftime("%d/%m/%Y")
    
    if df_agenda is not None and not df_agenda.empty:
        col_aprov_plan = next((c for c in df_agenda.columns if "APROVA" in c.upper() and "PLAN" in c.upper() or c.upper() == "APROVACAO"), "APROVACAO")
        col_aprov_exec = "VALIDACAO_GESTAO"
        col_just = "JUSTIFICATIVA" # Nome da coluna na planilha
        
        # Garantir que colunas existam
        if col_aprov_exec not in df_agenda.columns: df_agenda[col_aprov_exec] = "PENDENTE"
        if col_just not in df_agenda.columns: df_agenda[col_just] = ""

        # 1. Filtros Iniciais e Hierárquicos
        df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
        df_dia = df_dia[df_dia[col_aprov_plan].astype(str).str.upper() == "APROVADO"]
        
        if not (is_admin or is_diretoria):
            if is_analista: df_dia = df_dia[df_dia['ANALISTA'].str.upper() == user_atual]
            elif is_supervisor: df_dia = df_dia[df_dia['SUPERVISOR'].str.upper() == user_atual]
            else: df_dia = df_dia[df_dia['VENDEDOR'].str.upper() == user_atual]

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
                st.info("Valide os 'Realizados' por equipe ou vendedor.")
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
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                            st.success(f"{len(ids_m)} itens validados!"); time.sleep(1); st.rerun()
                        else: st.warning("Nada para processar.")

        # --- TABELA ---
        if not df_dia.empty:
            if df_base is not None: # Merge cidade
                df_cidades = df_base[['Cliente', 'Local']].copy()
                df_dia = pd.merge(df_dia, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left')
                df_dia.rename(columns={'Local': 'CIDADE'}, inplace=True)

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
                key="audit_dia",
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
                sel_row = df_dia.loc[idx]
                st.markdown("---")
                st.subheader(f"⚙️ Detalhes: {sel_row['CLIENTE']}")
                
                c1, c2, c3 = st.columns([1, 1, 1.5])
                with c1:
                    novo_status = st.selectbox("Status:", ["Planejado", "Realizado", "Reagendado"], 
                                             index=["Planejado", "Realizado", "Reagendado"].index(sel_row['STATUS']) if sel_row['STATUS'] in ["Planejado", "Realizado", "Reagendado"] else 0)
                with c2:
                    nova_val = st.radio("Validar:", ["PENDENTE", "OK", "REPROVADO"], 
                                      index=["PENDENTE", "OK", "REPROVADO"].index(sel_row[col_aprov_exec]) if sel_row[col_aprov_exec] in ["PENDENTE", "OK", "REPROVADO"] else 0, horizontal=True) if eh_gestao else sel_row[col_aprov_exec]
                
                with c3:
                    opcoes_just = ["", "Cliente Fechado", "Proprietário Ausente", "Sem estoque para o pedido", "Reagendado a pedido do cliente", "Visita produtiva com pedido", "Visita improdutiva", "Outros (especificar)"]
                    val_atual_just = sel_row[col_just] if pd.notna(sel_row[col_just]) else ""
                    default_idx = opcoes_just.index(val_atual_just) if val_atual_just in opcoes_just else 0
                    nova_just = st.selectbox("Escolha a Justificativa:", opcoes_just, index=default_idx)
                    if nova_just == "Outros (especificar)":
                        nova_just = st.text_input("Especifique o motivo:", value=val_atual_just if val_atual_just not in opcoes_just else "")

                if st.button("💾 SALVAR ATUALIZAÇÃO"):
                    lat_v = st.session_state.get('lat', 0); lon_v = st.session_state.get('lon', 0)
                    df_agenda.loc[df_agenda['ID'] == str(sel_row['ID']), ['STATUS', col_aprov_exec, col_just, 'COORDENADAS']] = [novo_status, nova_val, nova_just, f"{lat_v}, {lon_v}"]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.success("Dados atualizados!"); time.sleep(1); st.rerun()

            # --- BOTÃO ROTA FINALIZADA ---
           # --- BOTÃO ROTA FINALIZADA ---
# --- BOTÃO ROTA FINALIZADA ---
        st.markdown("---")
        if not df_dia.empty:
            if st.button("🚩 FINALIZAR ROTA E ENVIAR RESUMO", use_container_width=True, type="primary"):
                
                # 1. Busca Analista
                try:
                    analista_encontrado = df_base[df_base['VENDEDOR'].str.upper() == user_atual]['ANALISTA'].iloc[0].upper().strip()
                except:
                    analista_encontrado = "NÃO LOCALIZADO"

                # 2. Prepara Destinatários
                lista_final = EMAILS_GESTAO.copy()
                if analista_encontrado in MAPA_EMAILS:
                    lista_final.extend(MAPA_EMAILS[analista_encontrado])
                string_destinatarios = ", ".join(lista_final)

                # 3. Prepara Dados do Resumo
                resumo_dados = {
                    'total': len(df_dia),
                    'realizados': len(df_dia[df_dia['STATUS'] == "Realizado"]),
                    'pedidos': len(df_dia[df_dia['JUSTIFICATIVA'] == "Visita produtiva com pedido"]),
                    'pendentes': len(df_dia[df_dia['STATUS'] != "Realizado"])
                }

                # 4. Cálculos Adicionais
                # Taxa: Pedidos divididos pelas visitas que ele DE FATO fez
                taxa_conversao = (resumo_dados['pedidos'] / resumo_dados['realizados'] * 100) if resumo_dados['realizados'] > 0 else 0
                
                # Hora usando o fuso horário configurado no seu app
                hora_finalizacao = datetime.now(fuso_br).strftime("%H:%M:%S")
                
                # Link do GPS
                link_mapas = f"https://www.google.com/maps?q={st.session_state.lat},{st.session_state.lon}"

                # 5. Envio Final
                with st.spinner(f"Enviando resumo para {analista_encontrado}..."):
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
                    st.success(f"✅ Rota finalizada! Resumo enviado.")
                    st.balloons()
    else:
        st.error("Falha ao enviar e-mail. Verifique as credenciais.")
                    
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

        # --- MAPA DE CALOR ---
        st.markdown("---")
        st.subheader("🔥 Mapa de Calor")
        tipo_mapa = st.radio("Selecione a camada:", ["Visitas Realizadas", "Faturamento (Pedidos)"], horizontal=True)
        try:
            import folium
            from folium.plugins import HeatMap
            from streamlit_folium import st_folium
            if tipo_mapa == "Visitas Realizadas":
                df_mapa = df_agenda[(df_agenda['STATUS'] == "Realizado") & (df_agenda['COORDENADAS'].astype(str).str.contains(',', na=False))].copy()
            else:
                df_mapa = df_comp[(df_comp['Qtd_Pedidos'] > 0) & (df_comp['COORDENADAS'].astype(str).str.contains(',', na=False))].copy()
            
            if not df_mapa.empty:
                df_mapa[['lat', 'lon']] = df_mapa['COORDENADAS'].str.split(',', expand=True).astype(float)
                m = folium.Map(location=[df_mapa['lat'].mean(), df_mapa['lon'].mean()], zoom_start=7, tiles="cartodbpositron")
                HeatMap(df_mapa[['lat', 'lon']].dropna().values.tolist(), radius=15).add_to(m)
                st_folium(m, width="100%", height=500, returned_objects=[])
        except: 
            st.info("Aguardando coordenadas válidas.")
# Seria útil eu gerar um resumo de quantos clientes faltam agendar por cidade agora?
# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    
    if df_base is not None:
        # Mapeamento das colunas da BASE
        col_ana_base = 'ANALISTA'
        col_sup_base = 'SUPERVISOR'
        col_ven_base = 'VENDEDOR' 

        # --- LÓGICA DE FILTROS CASCATA ---
        if is_admin or is_diretoria:
            lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
            ana_sel = st.selectbox("1. Filtrar por Analista:", ["Todos"] + lista_analistas)
            df_sup_f = df_base if ana_sel == "Todos" else df_base[df_base[col_ana_base] == ana_sel]
            lista_sups = sorted([str(s) for s in df_sup_f[col_sup_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
            sup_sel = st.selectbox("2. Filtrar por Supervisor:", ["Todos"] + lista_sups)
            df_ven_f = df_sup_f if sup_sel == "Todos" else df_sup_f[df_sup_f[col_sup_base] == sup_sel]
            vends = sorted([str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()])
            ven_sel = st.selectbox("3. Selecione o Vendedor:", ["Selecione..."] + vends)

        elif is_analista:
            df_ana_f = df_base[df_base[col_ana_base].str.upper() == user_atual]
            lista_sups = sorted([str(s) for s in df_ana_f[col_sup_base].unique() if str(s).strip()])
            sup_sel = st.selectbox("1. Filtrar seu Supervisor:", ["Todos"] + lista_sups)
            df_ven_f = df_ana_f if sup_sel == "Todos" else df_ana_f[df_ana_f[col_sup_base] == sup_sel]
            vends = sorted([str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()])
            ven_sel = st.selectbox("2. Selecione o Vendedor:", ["Selecione..."] + vends)

        elif any(df_base[col_sup_base].str.upper() == user_atual):
            df_ven_f = df_base[df_base[col_sup_base].str.upper() == user_atual]
            vends_equipe = [str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()]
            lista_final_vends = sorted(list(set(vends_equipe + [user_atual])))
            ven_sel = st.selectbox("Selecione para quem agendar:", ["Selecione..."] + lista_final_vends)
        
        else:
            ven_sel = user_atual
            st.info(f"Agendando para sua própria base: {user_atual}")

        # --- VERIFICAÇÃO DE PUNIÇÃO (TRAVA) ---
        bloqueado = False
        if ven_sel != "Selecione...":
            hoje_dt = datetime.now(fuso_br).date()
            
            # Filtrar agendamentos passados do vendedor que ainda estão "Planejado"
            df_verif = df_agenda[df_agenda['VENDEDOR'].str.upper() == ven_sel.upper()].copy()
            
            if not df_verif.empty:
                df_verif['DT_OBJ'] = pd.to_datetime(df_verif['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                pendencias_passadas = df_verif[
                    (df_verif['DT_OBJ'] < hoje_dt) & 
                    (df_verif['STATUS'] == "Planejado")
                ]

                if not pendencias_passadas.empty:
                    bloqueado = True
                    st.error(f"⚠️ **AGENDAMENTO BLOQUEADO PARA {ven_sel}**")
                    st.warning(f"O colaborador possui {len(pendencias_passadas)} visitas de dias anteriores sem atualização de status. É necessário finalizar a rota dos dias passados (Realizado ou Justificado) antes de criar novos agendamentos.")
                    with st.expander("Ver visitas pendentes de atualização"):
                        st.table(pendencias_passadas[['DATA', 'CLIENTE', 'STATUS']].sort_values(by='DATA'))

        # --- PROCESSAMENTO DO AGENDAMENTO (SÓ EXIBE SE NÃO ESTIVER BLOQUEADO) ---
        if ven_sel != "Selecione..." and not bloqueado:
            clientes_f = df_base[df_base[col_ven_base] == ven_sel]
            if clientes_f.empty and ven_sel == user_atual:
                clientes_f = df_base[df_base[col_sup_base] == user_atual]

            if 'VENDEDOR' not in df_agenda.columns: df_agenda['VENDEDOR'] = ""

            codigos_agendados = df_agenda[
                (df_agenda['VENDEDOR'] == ven_sel) & 
                (df_agenda['STATUS'].isin(['Planejado', 'Realizado']))
            ]['CÓDIGO CLIENTE'].unique()
            
            clientes_pendentes = clientes_f[~clientes_f['Cliente'].isin(codigos_agendados)]
            
            # --- MÉTRICAS DE ENGAJAMENTO ---
            m1, m2, m3, m4 = st.columns(4)
            n_total = len(clientes_f)
            n_agendados = len(codigos_agendados)
            n_pend_metric = len(clientes_pendentes)
            m1.metric("Clientes na Base", n_total)
            m2.metric("Já Agendados", n_agendados)
            m3.metric("Faltando", n_pend_metric)
            m4.metric("% Adesão", f"{(n_agendados/n_total*100 if n_total>0 else 0):.1f}%")
            
            # Identificação dos vínculos para salvar
            try:
                amostra = clientes_f.iloc[0]
                analista_vinc = str(amostra[col_ana_base]).upper()
                supervisor_vinc = str(amostra[col_sup_base]).upper()
            except:
                analista_vinc = "N/I"
                supervisor_vinc = user_atual if ven_sel == user_atual else "N/I"

            lista_c = sorted(clientes_pendentes.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            
            if not lista_c:
                st.success(f"✅ Todos os clientes de {ven_sel} já foram agendados!")
            else:
                cliente_sel = st.selectbox("Selecione o Cliente (Apenas Pendentes):", ["Selecione..."] + lista_c)
                if cliente_sel != "Selecione...":
                    qtd_visitas = st.number_input("Quantidade de visitas (Máx 4):", min_value=1, max_value=4, value=1)
                    
                    with st.form("form_novo_v"):
                        cols_datas = st.columns(qtd_visitas)
                        datas_sel = []
                        for i in range(qtd_visitas):
                            with cols_datas[i]:
                                # Trava de data: Não permite retroativo (min_value=hoje_dt)
                                d = st.date_input(f"Data {i+1}:", value=hoje_dt, min_value=hoje_dt, key=f"d_{i}")
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
                                    "SUPERVISOR": supervisor_vinc, 
                                    "VENDEDOR": ven_sel,
                                    "CÓDIGO CLIENTE": cod_c, 
                                    "CLIENTE": nom_c, 
                                    "JUSTIFICATIVA": "-", 
                                    "STATUS": "Planejado",
                                    "AGENDADO POR": user_atual 
                                })
                                
                            df_final_a = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas_linhas)], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                            st.cache_data.clear()
                            st.success(f"✅ Agendado com sucesso!")
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
    # --- CABEÇALHO COM BOTÃO DE ATUALIZAR ---
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("🔍 Minha Agenda Completa")
    
    with col_btn:
        if st.button("🔄 Atualizar Dados", key="btn_refresh_agenda"):
            st.cache_data.clear()
            st.rerun()
    
    if df_agenda is not None and not df_agenda.empty:
        # 1. Limpeza e Padronização Inicial
        for col in ['APROVACAO', 'OBS_GESTAO', 'ANALISTA', 'SUPERVISOR', 'VENDEDOR']:
            if col not in df_agenda.columns: 
                df_agenda[col] = ""
            else:
                if col == 'APROVACAO':
                    df_agenda[col] = df_agenda[col].fillna("Pendente").replace(["", "none", "None", "nan", "NaN"], "Pendente")
                else:
                    df_agenda[col] = df_agenda[col].fillna("").replace(["none", "None", "nan", "NaN"], "")

        # --- PREPARAÇÃO PARA PREVISIBILIDADE ---
        df_agenda['DT_COMPLETA'] = pd.to_datetime(df_agenda['DATA'], dayfirst=True, errors='coerce')
        dias_traducao = {
            'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
            'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df_agenda['DIA_SEMANA'] = df_agenda['DT_COMPLETA'].dt.day_name().map(dias_traducao)

        # --- LÓGICA DE FILTRO POR HIERARQUIA ---
        if is_admin or is_diretoria:
            df_user = df_agenda.copy()
            st.info("💡 Visão de Administrador: Todos os registros exibidos.")
        elif is_analista:
            df_user = df_agenda[df_agenda['ANALISTA'].str.upper() == user_atual].copy()
        elif is_supervisor:
            df_user = df_agenda[df_agenda['SUPERVISOR'].str.upper() == user_atual].copy()
        else:
            df_user = df_agenda[df_agenda['VENDEDOR'].str.upper() == user_atual].copy()

        if not df_user.empty:
            # Filtros dinâmicos
            with st.expander("🎯 Filtros de Visualização", expanded=False):
                f_col1, f_col2, f_col3 = st.columns(3)
                
                def get_options(df, col):
                    return ["Todos"] + sorted([str(x) for x in df[col].unique() if x])

                ana_f = f_col1.selectbox("Filtrar Analista:", get_options(df_user, 'ANALISTA'))
                mask_sup = df_user['ANALISTA'] == ana_f if ana_f != "Todos" else df_user['ANALISTA'].notnull()
                
                sup_f = f_col2.selectbox("Filtrar Supervisor:", get_options(df_user[mask_sup], 'SUPERVISOR'))
                mask_vend = (mask_sup) & (df_user['SUPERVISOR'] == sup_f if sup_f != "Todos" else df_user['SUPERVISOR'].notnull())
                
                vend_f = f_col3.selectbox("Filtrar Vendedor:", get_options(df_user[mask_vend], 'VENDEDOR'))
                
                if ana_f != "Todos": df_user = df_user[df_user['ANALISTA'] == ana_f]
                if sup_f != "Todos": df_user = df_user[df_user['SUPERVISOR'] == sup_f]
                if vend_f != "Todos": df_user = df_user[df_user['VENDEDOR'] == vend_f]

            # --- CÁLCULO DOS CONTADORES ---
            def extrair_dist(val):
                try:
                    s = str(val).replace('m', '').replace('Erro GPS', '0')
                    return float(s) if (s != 'nan' and s.strip() != "") else 0
                except: return 0
            
            df_user['dist_val_calc'] = df_user['DISTANCIA_LOG'].apply(extrair_dist) if 'DISTANCIA_LOG' in df_user.columns else 0

            # --- EXIBIÇÃO DOS CARDS ---
            total_agendado = len(df_user)
            total_pendente = len(df_user[df_user['STATUS'] == "Planejado"])
            total_realizado = len(df_user[df_user['STATUS'] == "Realizado"])
            
            cols_metrics = st.columns(4 if (is_admin or is_diretoria or is_analista) else 3)
            cols_metrics[0].metric("📅 Total Agendado", total_agendado)
            cols_metrics[1].metric("⏳ Total Pendente", total_pendente)
            cols_metrics[2].metric("✅ Total Realizado", total_realizado)
            
            if len(cols_metrics) == 4:
                fora_raio = len(df_user[(df_user['STATUS'] == "Realizado") & (df_user['dist_val_calc'] > 50)])
                cols_metrics[3].metric("📍 Fora do Raio (>50m)", fora_raio, delta=f"{fora_raio} Alertas" if fora_raio > 0 else None, delta_color="inverse")
            
            st.markdown("---")

            # --- PAINEL DE APROVAÇÃO EM MASSA (Opcional para gestores) ---
            if (is_admin or is_diretoria or is_analista) and not df_user.empty:
                with st.expander("⚖️ Painel de Aprovação de Agendas", expanded=False):
                    col_ap1, col_ap2, col_ap3 = st.columns([2, 2, 3])
                    vends_na_lista = sorted([str(x) for x in df_user['VENDEDOR'].unique() if x])
                    vend_alvo = col_ap1.selectbox("Ação em Massa para Vendedor:", ["Todos"] + vends_na_lista)
                    status_massa = col_ap2.selectbox("Definir como:", ["Aprovado", "Reprovado"])
                    obs_massa = col_ap3.text_input("Observação da Gestão:", placeholder="Digite o motivo...", key="obs_massa_input")
                    
                    if st.button("🚀 Aplicar Decisão em Massa"):
                        mask = df_agenda['VENDEDOR'] == vend_alvo if vend_alvo != "Todos" else df_agenda['VENDEDOR'].isin(vends_na_lista)
                        df_agenda.loc[mask, 'APROVACAO'] = status_massa
                        df_agenda.loc[mask, 'OBS_GESTAO'] = obs_massa
                        if status_massa == "Reprovado":
                            df_agenda.loc[mask, 'STATUS'] = "Reprovado"
                        
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'dist_val_calc'], errors='ignore'))
                        st.cache_data.clear()
                        st.success("Agendas atualizadas!"); time.sleep(1); st.rerun()

            # Traz Cidade caso não exista
            if df_base is not None and 'CIDADE' not in df_user.columns:
                col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
                df_cidades = df_base[['Cliente', col_local_base]].copy()
                df_user = pd.merge(df_user, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left').drop(columns=['Cliente_y'], errors='ignore')
                df_user.rename(columns={col_local_base: 'CIDADE'}, inplace=True)

            # --- TABELA DE EXIBIÇÃO FINAL ---
            df_user["AÇÃO"] = False
            cols_display = [
                'AÇÃO', 'REGISTRO','DATA', 'VENDEDOR', 'CLIENTE', 'CIDADE', 
                'STATUS', 'DISTANCIA_LOG', 'COORDENADAS', 'APROVACAO', 'OBS_GESTAO'
            ]

            # 2. TRAVA DE SEGURANÇA: Se NÃO for Admin/Diretoria/Analista, removemos o GPS
            if not (is_admin or is_diretoria or is_analista):
                if 'DISTANCIA_LOG' in cols_display: cols_display.remove('DISTANCIA_LOG')
                if 'COORDENADAS' in cols_display: cols_display.remove('COORDENADAS')
                    
            cols_presentes = [c for c in cols_display if c in df_user.columns]
            df_display = df_user[cols_presentes].copy()

            def style_agenda(row):
                if row.get('APROVACAO') == "Reprovado": return ['background-color: #fadbd8'] * len(row)
                if row.get('APROVACAO') == "Aprovado": return ['background-color: #d4efdf'] * len(row)
                return [''] * len(row)

            # 4. Renderização da Tabela
            edicao_user = st.data_editor(
                df_display.style.apply(style_agenda, axis=1), 
                key="edit_agenda_final", 
                hide_index=True, 
                use_container_width=True, 
                column_config={
                    "AÇÃO": st.column_config.CheckboxColumn("📌"),
                    "REGISTRO": st.column_config.TextColumn("📅 Criado em"),
                    "DISTANCIA_LOG": st.column_config.TextColumn("Metros"),
                    "COORDENADAS": st.column_config.TextColumn("Localização (GPS)")
                },
                disabled=[c for c in cols_presentes if c != "AÇÃO"]
            )
            
            # --- GERENCIAMENTO INDIVIDUAL ---
            marcados = edicao_user[edicao_user["AÇÃO"] == True]
            if not marcados.empty:
                idx = marcados.index[0]
                sel_row = df_user.iloc[idx]
                st.markdown(f"### ⚙️ Gerenciar: {sel_row['CLIENTE']}")
                
                tabs = st.tabs(["⚖️ Aprovação", "🔄 Reagendar", "🗑️ Excluir"])
                
                with tabs[0]:
                    if is_admin or is_diretoria or is_analista:
                        motivo_atual = str(sel_row['OBS_GESTAO']) if pd.notnull(sel_row['OBS_GESTAO']) and str(sel_row['OBS_GESTAO']).lower() != "nan" else ""
                        n_ap = st.selectbox("Decisão:", ["Aprovado", "Reprovado"], key="ind_v")
                        n_ob = st.text_input("Motivo da Decisão:", value=motivo_atual, key="motivo_ind")
                        
                        if st.button("Salvar Decisão Individual"):
                            df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'APROVACAO'] = n_ap
                            df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'OBS_GESTAO'] = n_ob
                            if n_ap == "Reprovado": df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Reprovado"
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'dist_val_calc'], errors='ignore'))
                            st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()
                    else: st.warning("Apenas gestores podem aprovar.")

                with tabs[1]:
                    n_dt = st.date_input("Nova Data:", value=datetime.now())
                    if st.button("Confirmar Reagendamento"):
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'DATA'] = n_dt.strftime('%d/%m/%Y')
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Planejado"
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'APROVACAO'] = "Pendente"
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'dist_val_calc'], errors='ignore'))
                        st.cache_data.clear(); st.success("Reagendado!"); time.sleep(1); st.rerun()
                
                with tabs[2]:
                    if st.button("Confirmar Exclusão Definitiva"):
                        df_new = df_agenda[df_agenda['ID'] != sel_row['ID']]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_new.drop(columns=['LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'dist_val_calc'], errors='ignore'))
                        st.cache_data.clear(); st.success("Removido!"); time.sleep(1); st.rerun()
        else:
            st.info("Nenhum agendamento encontrado.")
    else:
        st.warning("Agenda vazia.")

# --- PÁGINA: DESEMPENHO DE VENDAS (FATURADO) ---
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

        # Tratamento META SISTEMA
        if df_meta_sistema is not None:
            df_meta_sistema.columns = [str(c).strip() for c in df_meta_sistema.columns]
            df_meta_sistema['RG'] = df_meta_sistema['RG'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_meta_sistema['QTD'] = pd.to_numeric(df_meta_sistema['QTD'], errors='coerce').fillna(0)
            if 'HIERARQUIA DE PRODUTOS' in df_meta_sistema.columns:
                df_meta_sistema['HIERARQUIA DE PRODUTOS'] = df_meta_sistema['HIERARQUIA DE PRODUTOS'].astype(str).str.strip().str.upper()

        # Tratamento META 2025
        if df_2025 is not None:
            df_2025.columns = [str(c).strip() for c in df_2025.columns]
            df_2025['RG'] = df_2025['RG'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_2025['QUANTIDADE'] = pd.to_numeric(df_2025['QUANTIDADE'], errors='coerce').fillna(0)
            if 'HIERARQUIA DE PRODUTOS' in df_2025.columns:
                df_2025['HIERARQUIA DE PRODUTOS'] = df_2025['HIERARQUIA DE PRODUTOS'].astype(str).str.strip().str.upper()

        if df_faturado is not None and not df_faturado.empty:
            df_faturado = df_faturado.dropna(how='all')
            df_faturado.columns = [str(c).strip() for c in df_faturado.columns]
            
            df_faturado.rename(columns={
                'Região de vendas': 'VENDEDOR_NOME',
                'RG': 'VENDEDOR_COD', 
                'Qtd Vendas (S/Dec)': 'QTD_VENDAS',
                'Hierarquia de produtos': 'HIERARQUIA'
            }, inplace=True)

            df_faturado['QTD_VENDAS'] = pd.to_numeric(df_faturado['QTD_VENDAS'], errors='coerce').fillna(0)
            df_faturado['VENDEDOR_COD'] = df_faturado['VENDEDOR_COD'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            def aplicar_agrupamento_custom(item):
                item = str(item).strip().upper()
                mapeamento = {
                    'DESCARTAVEIS COPOS': 'DESCARTAVEIS', 'DESCARTAVEIS PRATOS': 'DESCARTAVEIS', 
                    'DESCARTAVEIS TAMPAS': 'DESCARTAVEIS', 'DESCARTAVEIS POTES': 'DESCARTAVEIS',
                    'MILHO CANJICA': 'MILHO', 'MILHO CANJIQUINHA': 'MILHO', 
                    'MILHO CREME MILHO': 'MILHO', 'MILHO FUBA': 'MILHO',
                    'MOLHOS ALHO PICANTE': 'MOLHOS ALHO',
                    'PIMENTA CONSERVA BIQUINHO': 'PIMENTA CONSERVA', 
                    'PIMENTA CONSERVA PASTA': 'PIMENTA CONSERVA'
                }
                return mapeamento.get(item, item)
            
            df_faturado['HIERARQUIA'] = df_faturado['HIERARQUIA'].apply(aplicar_agrupamento_custom)
            df_relacao = df_base[['VENDEDOR', 'SUPERVISOR', 'ANALISTA']].drop_duplicates(subset=['VENDEDOR'])
            df_faturado = pd.merge(df_faturado, df_relacao, left_on='VENDEDOR_NOME', right_on='VENDEDOR', how='left')
            df_faturado['ANALISTA'] = df_faturado['ANALISTA'].fillna('NÃO CADASTRADO')
            df_faturado['SUPERVISOR'] = df_faturado['SUPERVISOR'].fillna('NÃO CADASTRADO')
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
            df_metas_cob['EscrV'] = df_metas_cob['EscrV'].astype(str).str.strip()
            if 'HIERARQUIA DE PRODUTOS' in df_metas_cob.columns:
                df_metas_cob['HIERARQUIA DE PRODUTOS'] = df_metas_cob['HIERARQUIA DE PRODUTOS'].astype(str).str.strip().str.upper()
            df_metas_cob['BASE'] = pd.to_numeric(df_metas_cob['BASE'], errors='coerce').fillna(0)
            metas_vend_raw = pd.to_numeric(df_metas_cob['META'].astype(str).str.replace('%','').str.replace(',','.'), errors='coerce').fillna(0)
            df_metas_cob['META'] = metas_vend_raw.apply(lambda x: x * 100 if x > 0 and x <= 1.0 else x)
            if 'META COBERTURA' in df_metas_cob.columns:
                metas_cob_item = pd.to_numeric(df_metas_cob['META COBERTURA'].astype(str).str.replace('%','').str.replace(',','.'), errors='coerce').fillna(0)
                df_metas_cob['META COBERTURA'] = metas_cob_item.apply(lambda x: x * 100 if x > 0 and x <= 1.0 else x)

    except Exception as e:
        st.error(f"Erro no processamento das abas: {e}")
        st.stop()

    if df_faturado is not None and not df_faturado.empty:
        df_f = df_faturado.copy()
        df_ms = df_meta_sistema.copy() if df_meta_sistema is not None else None
        df_25 = df_2025.copy() if df_2025 is not None else None
        
        st.markdown("### 🔍 Filtros")
        c0, c2, c3 = st.columns(3)
        
        with c0:
            sel_estado = st.multiselect("Estado", sorted(df_f['EscrV'].dropna().unique()))
        
        with c2:
            df_temp_sup = df_f[df_f['EscrV'].isin(sel_estado)] if sel_estado else df_f
            sel_supervisor = st.multiselect("Supervisor", sorted(df_temp_sup['SUPERVISOR'].dropna().unique()))
            
        with c3:
            df_temp_vend = df_temp_sup[df_temp_sup['SUPERVISOR'].isin(sel_supervisor)] if sel_supervisor else df_temp_sup
            sel_vendedor = st.multiselect("Vendedor", sorted(df_temp_vend['VENDEDOR_NOME'].dropna().unique()))

        if sel_estado: 
            df_f = df_f[df_f['EscrV'].isin(sel_estado)]
            if df_ms is not None: df_ms = df_ms[df_ms['EscrV'].isin(sel_estado)]
        if sel_supervisor: 
            df_f = df_f[df_f['SUPERVISOR'].isin(sel_supervisor)]
            if df_ms is not None: df_ms = df_ms[df_ms['EqvS'].isin(sel_supervisor)]
        if sel_vendedor: 
            df_f = df_f[df_f['VENDEDOR_NOME'].isin(sel_vendedor)]
            
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

            st.markdown("---")
            m1, m2, m3 = st.columns([1, 1, 2])
            m1.metric("📦 Volume Total", f"{df_f['QTD_VENDAS'].sum():,.0f}".replace(",", "."))
            m2.metric("🏪 Positivados", f"{positivacao:,.0f}".replace(",", "."))
            
            with m3:
                estados_str = ", ".join(map(str, df_f['EscrV'].unique()))
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                    <small style="color: #666;">COBERTURA ({estados_str})</small><br>
                    <span style="font-size: 1.1em;">Base: <b>{base_total:,.0f}</b> | Meta: <b>{meta_val:.0f}%</b></span><br>
                    Atingido: <span style="color:{cor_indicador}; font-size: 1.4em; font-weight: bold;">{real_perc:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("### 📈 Desempenho por Hierarquia")
        
        # Agrupamentos
        df_f_agrupado = df_f.groupby('HIERARQUIA').agg({'QTD_VENDAS': 'sum', col_k: 'nunique'}).rename(columns={'QTD_VENDAS': 'VOLUME', col_k: 'POSITIVADO_REAL'}).reset_index()

        df_ms_agrupado = df_ms.groupby('HIERARQUIA DE PRODUTOS')['QTD'].sum().reset_index().rename(columns={'HIERARQUIA DE PRODUTOS': 'HIERARQUIA', 'QTD': 'META 2026'}) if df_ms is not None else pd.DataFrame(columns=['HIERARQUIA', 'META 2026'])
        df_25_agrupado = df_25.groupby('HIERARQUIA DE PRODUTOS')['QUANTIDADE'].sum().reset_index().rename(columns={'HIERARQUIA DE PRODUTOS': 'HIERARQUIA', 'QUANTIDADE': 'META 2025'}) if df_25 is not None else pd.DataFrame(columns=['HIERARQUIA', 'META 2025'])

        # Cruzamento Cobertura
        df_metas_sub = df_metas_cob[df_metas_cob['EscrV'].isin(df_f['EscrV'].unique())] if not df_f.empty else df_metas_cob
        df_metas_hierarquia = df_metas_sub.groupby('HIERARQUIA DE PRODUTOS')['META COBERTURA'].mean().reset_index().rename(columns={'HIERARQUIA DE PRODUTOS': 'HIERARQUIA'}) if 'META COBERTURA' in df_metas_sub.columns else pd.DataFrame(columns=['HIERARQUIA', 'META COBERTURA'])

        # Merge Final
        df_final_h = pd.merge(pd.DataFrame(lista_hierarquia_fixa, columns=['HIERARQUIA']), df_f_agrupado, on='HIERARQUIA', how='left')
        df_final_h = pd.merge(df_final_h, df_metas_hierarquia, on='HIERARQUIA', how='left')
        df_final_h = pd.merge(df_final_h, df_25_agrupado, on='HIERARQUIA', how='left') 
        df_final_h = pd.merge(df_final_h, df_ms_agrupado, on='HIERARQUIA', how='left').fillna(0)
        
      # --- CÁLCULOS DE COBERTURA (CLIENTES) ---
        df_final_h['META CLIENTES (ABS)'] = (df_final_h['META COBERTURA'] / 100) * base_total
        df_final_h = df_final_h.rename(columns={'HIERARQUIA': 'HIERARQUIA DE PRODUTOS', 'POSITIVADO_REAL': 'POSITIVAÇÃO'})
        df_final_h['PENDÊNCIA CLIENTES'] = (df_final_h['META CLIENTES (ABS)'] - df_final_h['POSITIVAÇÃO']).clip(lower=0)

        # --- CÁLCULOS VOLUME 2025 ---
        df_final_h['CRESCIMENTO 2025'] = df_final_h['VOLUME'] - df_final_h['META 2025']
        df_final_h['ATINGIMENTO % (VOL 2025)'] = (df_final_h['VOLUME'] / df_final_h['META 2025'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)

        # --- CÁLCULOS VOLUME 2026 ---
        df_final_h['CRESCIMENTO 2026'] = df_final_h['VOLUME'] - df_final_h['META 2026']
        df_final_h['ATINGIMENTO % (VOL 2026)'] = (df_final_h['VOLUME'] / df_final_h['META 2026'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)

        # Reordenação final com TODAS as colunas solicitadas
        colunas_ordenadas = [
            'HIERARQUIA DE PRODUTOS', 
            'META COBERTURA', 
            'META CLIENTES (ABS)',
            'POSITIVAÇÃO', 
            'PENDÊNCIA CLIENTES',
            'META 2025', 
            'META 2026', 
            'VOLUME',
            'CRESCIMENTO 2025',
            'ATINGIMENTO % (VOL 2025)',
            'CRESCIMENTO 2026',
            'ATINGIMENTO % (VOL 2026)' # <-- A última coluna agora é o atingimento 2026
        ]
        
        df_final_h = df_final_h[colunas_ordenadas]
        
        st.dataframe(
            df_final_h.sort_values(by=['HIERARQUIA DE PRODUTOS'], ascending=True).style.format({
                'META COBERTURA': "{:.1f}%",
                'META CLIENTES (ABS)': lambda x: f"{x:,.0f}".replace(",", "."),
                'POSITIVAÇÃO': lambda x: f"{x:,.0f}".replace(",", "."), 
                'PENDÊNCIA CLIENTES': lambda x: f"{x:,.0f}".replace(",", "."), 
                'META 2025': lambda x: f"{x:,.0f}".replace(",", "."),
                'META 2026': lambda x: f"{x:,.0f}".replace(",", "."),
                'VOLUME': lambda x: f"{x:,.0f}".replace(",", "."),
                'CRESCIMENTO 2025': lambda x: f"{x:,.0f}".replace(",", "."),
                'ATINGIMENTO % (VOL 2025)': "{:.1f}%",
                'CRESCIMENTO 2026': lambda x: f"{x:,.0f}".replace(",", "."),
                'ATINGIMENTO % (VOL 2026)': "{:.1f}%" # <-- Formatação final
            }), 
            use_container_width=True, 
            hide_index=True
        )
