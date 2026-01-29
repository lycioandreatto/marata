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
st.set_page_config(page_title="Maratá - SCA", page_icon="📅", layout="wide")

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
    # Este bloco cria um "container" onde a logo e o texto ficam lado a lado
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
            <img src="https://raw.githubusercontent.com/lycioandreatto/marata/main/pngmarata" width="60">
            <h1 style="color: #000C75; margin: 0;">SISTEMA DE CONTROLE DE AGENDAMIENTOS</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_login, tab_cadastro = st.tabs(["Login", "Novo Cadastro"])
    # ... resto do código ...
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
# Se o código chegou aqui, o usuário está logado.
# Verificamos se a localização já foi capturada nesta sessão.
if "lat" not in st.session_state:
    with st.container():
        # Aviso visual para o usuário autorizar o navegador
        st.info("📡 **Conectando...** Por favor, autorize a localização no seu navegador para carregar o sistema.")
        
        # Chama a função do seu arquivo geoloc.py
        lat, lon = capturar_coordenadas()
        
        if lat and lon:
            st.session_state.lat = lat
            st.session_state.lon = lon
            st.success(f"📍 GPS Ativo: {lat:.4f}, {lon:.4f}")
            time.sleep(1) 
            st.rerun() # Recarrega para limpar a mensagem e carregar o menu
        else:
            st.warning("⚠️ **Acesso Negado ou GPS Desligado.** O sistema Maratá exige geolocalização para registro de visitas.")
            if st.button("🔄 Tentar capturar novamente"):
                st.rerun()
            st.stop() # Bloqueia o carregamento do Menu e Dados se não tiver GPS

# ==============================================================================
# O RESTO DO SEU CÓDIGO CONTINUA ABAIXO:
# ==============================================================================

# --- PERFIL DO USUÁRIO ---
user_atual = st.session_state.usuario
# ...
# --- PERFIL DO USUÁRIO ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual in LISTA_ANALISTA)
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

# Definindo ícone e label com base no perfil
if is_admin:
    label_display = "ADMINISTRADOR"
    user_icon = "👑"
    border_color = "#FFD700"  # Dourado para ADM
elif is_diretoria:
    label_display = f"{user_atual} | DIRETORIA"
    user_icon = "📈"
    border_color = "#1E90FF"
elif is_analista:
    label_display = f"{user_atual} | ANALISTA"
    user_icon = "🔬"
    border_color = "#9370DB"
else:
    label_display = f"{user_atual} | SUPERVISOR"
    user_icon = "👤"
    border_color = "#ff4b4b"

# --- BARRA LATERAL ---
with st.sidebar:
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
        
    for _ in range(8):
        st.sidebar.write("")
    st.markdown("---")
    st.subheader("🗑️ Limpeza em Massa")
    if df_agenda is not None and not df_agenda.empty:
        if is_admin or is_diretoria:
            # Adm e Diretoria vêem todos
            lista_sups = sorted(df_agenda['SUPERVISOR'].unique())
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups)
        elif is_analista:
            # O SEGREDO ESTÁ AQUI: Filtra a agenda apenas para os supervisores da THAIS (ou analista logado)
            df_agenda_analista = df_agenda[df_agenda['ANALISTA'].str.upper() == user_atual]
            lista_sups = sorted(df_agenda_analista['SUPERVISOR'].unique())
            sup_limpar = st.selectbox("Limpar agenda de:", ["Selecione..."] + lista_sups)
        else:
            # Supervisor comum não tem selectbox, só botão para ele mesmo
            sup_limpar = "Selecione..."

        # Lógica do Botão de Deletar com Confirmação
        if is_admin or is_analista or is_diretoria:
            if sup_limpar != "Selecione...":
                # Criamos um popover para confirmação
                confirma = st.popover(f"⚠️ APAGAR TUDO: {sup_limpar}")
                confirma.warning(f"Isso apagará permanentemente todos os registros de {sup_limpar}. Confirma?")
                if confirma.button(f"Sim, deletar agenda de {sup_limpar}", key="conf_del_adm"):
                    # Remove apenas o supervisor selecionado da planilha toda
                    df_rest = df_agenda[df_agenda['SUPERVISOR'] != sup_limpar].drop(columns=['LINHA'], errors='ignore')
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                    st.cache_data.clear()
                    st.success(f"Agenda de {sup_limpar} removida!")
                    time.sleep(1)
                    st.rerun()
        else:
            # Popover de confirmação para o próprio supervisor
            confirma_proprio = st.popover("⚠️ APAGAR TODA MINHA AGENDA")
            confirma_proprio.warning("Você tem certeza que deseja limpar toda a sua agenda?")
            if confirma_proprio.button("Sim, apagar tudo", key="conf_del_self"):
                df_rest = df_agenda[df_agenda['SUPERVISOR'] != user_atual].drop(columns=['LINHA'], errors='ignore')
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                st.cache_data.clear()
                st.success("Sua agenda foi limpa!")
                time.sleep(1)
                st.rerun()

# --- TÍTULO CENTRAL NO TOPO ---
st.markdown("<h4 style='text-align: center; color: black; margin-top: -110px;'>SISTEMA DE CONTROLE DE AGENDAMENTOS (SCA) - MARATÁ</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- PÁGINA: AGENDAMENTOS DO DIA ---
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

        total_visitas = len(df_dia)
        visitas_realizadas = len(df_dia[df_dia['STATUS'] == "Realizado"])

        m_col1, m_col2, m_col3 = st.columns([1, 1, 2])
        m_col1.metric("Visitas Hoje", total_visitas)
        m_col2.metric("Realizadas", visitas_realizadas, delta=f"{visitas_realizadas/total_visitas*100:.0f}%" if total_visitas > 0 else None)
        
        if not df_dia.empty:
            if df_base is not None:
                col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
                df_cidades = df_base[['Cliente', col_local_base]].copy()
                df_dia = pd.merge(df_dia, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left').drop(columns=['Cliente_y'], errors='ignore')
                df_dia.rename(columns={col_local_base: 'CIDADE'}, inplace=True)

            df_dia["EDITAR"] = False
            
            # --- CORREÇÃO DO ALERTA VISUAL ---
            def style_status(row):
                styles = [''] * len(row)
                if row['STATUS'] == "Realizado":
                    # Se houver distância salva e for maior que 500m
                    dist_str = str(row.get('DISTANCIA_LOG', '0')).replace('m', '').replace('Erro GPS', '0')
                    try:
                        dist_val = float(dist_str) if dist_str != 'nan' else 0
                        if dist_val > 500:
                            # COR LARANJA para alertas de distância
                            return ['color: #E67E22; font-weight: bold'] * len(row)
                    except:
                        pass
                    # COR VERDE para realizado normal
                    return ['color: green; font-weight: bold'] * len(row)
                return styles

            # Definindo colunas visíveis
            cols_v = ['EDITAR', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'CIDADE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']
            if is_admin or is_diretoria or is_analista:
                if 'DISTANCIA_LOG' in df_dia.columns:
                    cols_v.append('DISTANCIA_LOG')
            
            df_display = df_dia[cols_v].copy()
            df_styled = df_display.style.apply(style_status, axis=1)

            edicao_dia = st.data_editor(
                df_styled, 
                key="edit_dia", 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "EDITAR": st.column_config.CheckboxColumn("📝"),
                    "DISTANCIA_LOG": st.column_config.TextColumn("📍 Dist. GPS")
                },
                disabled=[c for c in cols_v if c != "EDITAR"]
            )

            marcados = edicao_dia[edicao_dia["EDITAR"] == True]
            if not marcados.empty:
                # Recupera o índice original para pegar os dados corretos
                idx_selecionado = marcados.index[0]
                sel_row = df_dia.iloc[idx_selecionado]
                
                st.markdown("---")
                st.subheader(f"Atualizar Atendimento: {sel_row['CLIENTE']}")
                st_list = ["Planejado", "Realizado", "Reagendado"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                col1, col2 = st.columns(2)
                with col1: 
                    n_st = st.radio("Status Atual:", st_list, index=st_list.index(sel_row['STATUS']) if sel_row['STATUS'] in st_list else 0)
                with col2:
                    n_ju = st.selectbox("Justificativa/Observação:", ju_list, index=ju_list.index(sel_row['JUSTIFICATIVA']) if sel_row['JUSTIFICATIVA'] in ju_list else 0)
                    mot_outro = st.text_input("Especifique:") if n_ju == "OUTRO" else ""

                if st.button("💾 ATUALIZAR STATUS"):
                    final_j = mot_outro if n_ju == "OUTRO" else n_ju
                    lat_v = st.session_state.get('lat', 0)
                    lon_v = st.session_state.get('lon', 0)
                    
                    cliente_info = df_base[df_base['Cliente'].astype(str) == str(sel_row['CÓDIGO CLIENTE'])]
                    log_distancia_valor = ""
                    alerta_distancia = False
                    
                    if not cliente_info.empty:
                        coord_base = cliente_info['COORDENADAS'].values[0]
                        if pd.notnull(coord_base) and "," in str(coord_base):
                            try:
                                partes = str(coord_base).split(",")
                                dist_m = calcular_distancia(lat_v, lon_v, partes[0].strip(), partes[1].strip())
                                log_distancia_valor = f"{dist_m:.0f}m"
                                if n_st == "Realizado" and dist_m > 50:
                                    alerta_distancia = True
                            except: log_distancia_valor = "Erro GPS"

                    # Gravação na Planilha
                    df_agenda.loc[df_agenda['ID'] == str(sel_row['ID']), ['STATUS', 'JUSTIFICATIVA', 'COORDENADAS', 'DISTANCIA_LOG']] = [n_st, final_j, f"{lat_v}, {lon_v}", log_distancia_valor]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    
                    st.cache_data.clear()
                    if alerta_distancia:
                        st.warning(f"⚠️ Visita registrada com distância excedida ({log_distancia_valor})!")
                        time.sleep(2)
                    else:
                        st.success("✅ Atualizado!")
                        time.sleep(1)
                    st.rerun()
        else:
            st.info(f"Não há agendamentos para hoje ({hoje_str}).")
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
        
        c1.metric("Total Clientes Base", total_base)
        c2.metric("Total Agendados", total_agendados)
        c3.metric("Pendente Total", total_pendente)
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

       # --- SEÇÃO: COMPARAÇÃO AGENDA VS FATURAMENTO ---
        st.markdown("---")
        st.subheader("🎯 Conversão de Agendamentos em Vendas")

        try:
            # 1. Leitura
            df_fat = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
            
            # 2. Limpeza de colunas e identificação
            df_fat.columns = [str(c).strip() for c in df_fat.columns]
            col_cod_cliente_fat = df_fat.columns[10] # Coluna K
            col_pedidos = "OrdCliente"
            col_data_fat_col = "Data fat."

            # --- TRATAMENTO BLINDADO ---
            def limpar_codigo(id_cliente):
                if pd.isna(id_cliente): return ""
                return str(id_cliente).split('.')[0].strip()

            df_fat['Cod_Limpo'] = df_fat[col_cod_cliente_fat].apply(limpar_codigo)
            
            # 4. Agrupamento: Pegamos a Qtd de pedidos e a ÚLTIMA data de faturamento
            df_fat_resumo = df_fat.groupby('Cod_Limpo').agg({
                col_pedidos: 'nunique',
                col_data_fat_col: 'max'
            }).reset_index()
            df_fat_resumo.columns = ['Cod_Cliente', 'Qtd_Pedidos', 'Ultima_Data_Fat']

            # 5. Cruzamento com a Agenda
            df_base_detalhe['Cliente_Limpo'] = df_base_detalhe['Cliente'].apply(limpar_codigo)
            
            df_comp = pd.merge(
                df_base_detalhe, 
                df_fat_resumo, 
                left_on='Cliente_Limpo', 
                right_on='Cod_Cliente', 
                how='left'
            ).fillna(0)

            # --- 6. CÁLCULO DOS INDICADORES ---
            df_agendados_ativos = df_comp[df_comp['STATUS AGENDAMENTO'] == 'AGENDADO'].copy()
            
            total_na_agenda = len(df_agendados_ativos)
            agendados_que_compraram = len(df_agendados_ativos[df_agendados_ativos['Qtd_Pedidos'] > 0])
            total_pedidos_agenda = df_agendados_ativos['Qtd_Pedidos'].sum()
            
            taxa_conversao = (agendados_que_compraram / total_na_agenda * 100) if total_na_agenda > 0 else 0

            # 7. EXIBIÇÃO CARDS
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Clientes Agendados", total_na_agenda)
            c2.metric("Agendados que Compraram", agendados_que_compraram)
            c3.metric("Taxa de Conversão", f"{taxa_conversao:.1f}%")
            c4.metric("Total de Pedidos (Agenda)", int(total_pedidos_agenda))

            # 8. Tabela de Apoio para conferência (FILTRADA PARA QUEM COMPROU)
            with st.expander("🔍 Ver detalhes da conversão (Auditoria)"):
                
                # --- ALTERAÇÃO AQUI: Filtrando para mostrar apenas quem tem pedidos > 0 ---
                df_convertidos = df_agendados_ativos[df_agendados_ativos['Qtd_Pedidos'] > 0].copy()
                
                # Formatação das datas para o padrão brasileiro
                df_convertidos['Data_Agendada_Format'] = pd.to_datetime(df_convertidos['REGISTRO'], errors='coerce').dt.strftime('%d/%m/%Y')
                df_convertidos['Data_Fat_Format'] = pd.to_datetime(df_convertidos['Ultima_Data_Fat'], errors='coerce').dt.strftime('%d/%m/%Y').fillna("-")
                
                # Seleção das colunas solicitadas
                df_view = df_convertidos[[
                    'Cliente', 
                    'Nome 1', 
                    col_ana_base, 
                    'Data_Agendada_Format', 
                    'Data_Fat_Format', 
                    'Qtd_Pedidos'
                ]]
                
                st.dataframe(
                    df_view.rename(columns={
                        'Nome 1': 'Nome do Cliente',
                        col_ana_base: 'Analista',
                        'Data_Agendada_Format': 'Data Agendada',
                        'Data_Fat_Format': 'Data Faturamento'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

        except Exception as e:
            st.error(f"Erro no processamento: {e}")

        
        # --- MAPA DE CALOR: DISTRIBUIÇÃO GEOGRÁFICA ---
        st.markdown("---")
        st.subheader("🔥 Distribuição Geográfica das Visitas (Realizadas)")
        
        # Filtramos visitas que tenham status "Realizado" e coordenadas válidas
        df_mapa = df_agenda[
            (df_agenda['STATUS'] == "Realizado") & 
            (df_agenda['COORDENADAS'].str.contains(',', na=False))
        ].copy()

        # Filtrar o mapa também pelos filtros de Analista/Supervisor do Dashboard
        if ana_sel_dash != "Todos":
             df_mapa = df_mapa[df_mapa['ANALISTA'].str.upper() == ana_sel_dash.upper()]
        if sup_sel_dash != "Todos":
             df_mapa = df_mapa[df_mapa['SUPERVISOR'] == sup_sel_dash]

        if not df_mapa.empty:
            try:
                import folium
                from folium.plugins import HeatMap
                from streamlit_folium import st_folium

                # Limpeza e conversão das coordenadas
                df_mapa[['lat', 'lon']] = df_mapa['COORDENADAS'].str.split(',', expand=True).astype(float)
                
                # Criar o mapa base centrado na média das coordenadas
                centro_lat = df_mapa['lat'].mean()
                centro_lon = df_mapa['lon'].mean()
                m = folium.Map(location=[centro_lat, centro_lon], zoom_start=7, tiles="cartodbpositron")
                
                # Gerar os dados de calor (latitude, longitude)
                dados_calor = df_mapa[['lat', 'lon']].values.tolist()
                HeatMap(dados_calor, radius=15, blur=10).add_to(m)
                
                # Renderizar no Streamlit
                st_folium(m, width="100%", height=500, returned_objects=[])
                
            except ImportError:
                st.warning("⚠️ Bibliotecas de mapa (folium/streamlit-folium) não instaladas.")
            except Exception as e:
                st.error(f"Erro ao gerar mapa: {e}")
        else:
            st.info("ℹ️ Nenhuma visita 'Realizada' com GPS encontrado para os filtros selecionados.")
        
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
            
            analista_vinc = user_atual if is_analista else "ADMIN"
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
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda Completa")
    
    if df_agenda is not None and not df_agenda.empty:
        # Filtro de visibilidade por perfil
        if is_admin or is_diretoria:
            df_user = df_agenda.copy()
        elif is_analista:
            df_user = df_agenda[df_agenda['ANALISTA'].str.upper() == user_atual].copy()
        else:
            df_user = df_agenda[df_agenda['SUPERVISOR'] == user_atual].copy()

        if not df_user.empty:
            # --- CÁLCULO DOS CONTADORES ---
            def extrair_dist(val):
                try:
                    s = str(val).replace('m', '').replace('Erro GPS', '0')
                    return float(s) if (s != 'nan' and s.strip() != "") else 0
                except: return 0
            
            df_user['dist_val_calc'] = df_user['DISTANCIA_LOG'].apply(extrair_dist)

            # --- EXIBIÇÃO DOS CARDS ---
            total_agendado = len(df_user)
            total_pendente = len(df_user[df_user['STATUS'] == "Planejado"])
            total_realizado = len(df_user[df_user['STATUS'] == "Realizado"])
            
            if is_admin or is_diretoria or is_analista:
                cols = st.columns(4)
                fora_raio = len(df_user[(df_user['STATUS'] == "Realizado") & (df_user['dist_val_calc'] > 500)])
                cols[3].metric("📍 Fora do Raio (>500m)", fora_raio, 
                              delta=f"{fora_raio} Alertas" if fora_raio > 0 else None, 
                              delta_color="inverse")
            else:
                cols = st.columns(3)

            cols[0].metric("📅 Total Agendado", total_agendado)
            cols[1].metric("⏳ Total Pendente", total_pendente)
            cols[2].metric("✅ Total Realizado", total_realizado)
            
            st.markdown("---")

            # Trazer Cidade
            if df_base is not None and 'CIDADE' not in df_user.columns:
                col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
                df_cidades = df_base[['Cliente', col_local_base]].copy()
                df_user = pd.merge(df_user, df_cidades, left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left').drop(columns=['Cliente_y'], errors='ignore')
                df_user.rename(columns={col_local_base: 'CIDADE'}, inplace=True)

            # Alteramos de EXCLUIR para AÇÃO para refletir as duas opções
            df_user["AÇÃO"] = False
            
            def style_agenda_completa(row):
                styles = [''] * len(row)
                if row['STATUS'] == "Realizado":
                    if row['dist_val_calc'] > 500:
                        return ['color: #E67E22; font-weight: bold'] * len(row)
                    return ['color: green; font-weight: bold'] * len(row)
                return styles

            cols_v = ['AÇÃO', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'CIDADE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR', 'dist_val_calc']
            if 'DISTANCIA_LOG' in df_user.columns:
                cols_v.append('DISTANCIA_LOG')

            df_display = df_user[cols_v].copy()
            df_styled = df_display.style.apply(style_agenda_completa, axis=1)

            # Ajuste de privacidade na visualização da coluna GPS
            config_col = {
                "AÇÃO": st.column_config.CheckboxColumn("📌"),
                "dist_val_calc": None
            }
            if not (is_admin or is_diretoria or is_analista):
                config_col["DISTANCIA_LOG"] = None
            else:
                config_col["DISTANCIA_LOG"] = st.column_config.TextColumn("📍 Dist. GPS")

            edicao_user = st.data_editor(
                df_styled, 
                key="edit_full_agenda_actions", 
                hide_index=True, 
                use_container_width=True,
                column_config=config_col,
                disabled=[c for c in cols_v if c != "AÇÃO"]
            )

            # LÓGICA DE GERENCIAMENTO (REAGENDAR OU EXCLUIR)
            marcados = edicao_user[edicao_user["AÇÃO"] == True]
            if not marcados.empty:
                idx = marcados.index[0]
                sel_row = df_user.iloc[idx]
                
                st.markdown(f"### ⚙️ Gerenciar: {sel_row['CLIENTE']}")
                t_re, t_ex = st.tabs(["🔄 Reagendar Visita", "🗑️ Excluir Registro"])
                
                with t_re:
                    st.write("Crie uma nova data para este cliente mantendo o histórico atual.")
                    n_data = st.date_input("Nova Data:", value=datetime.now())
                    if st.button("Confirmar Novo Agendamento"):
                        # Criar cópia e limpar dados de execução
                        nova_v = sel_row.copy()
                        nova_v['ID'] = str(uuid.uuid4())
                        nova_v['DATA'] = n_data.strftime('%d/%m/%Y')
                        nova_v['STATUS'] = "Planejado"
                        nova_v['JUSTIFICATIVA'] = ""
                        nova_v['DISTANCIA_LOG'] = ""
                        nova_v['COORDENADAS'] = ""
                        nova_v['AGENDADO POR'] = user_atual
                        
                        # Limpar colunas que não vão para a planilha
                        nova_v_dict = nova_v.drop(labels=['AÇÃO', 'dist_val_calc', 'CIDADE', 'LINHA'], errors='ignore').to_frame().T
                        
                        df_final = pd.concat([df_agenda, nova_v_dict], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final.drop(columns=['LINHA'], errors='ignore'))
                        st.cache_data.clear()
                        st.success("Nova visita agendada com sucesso!")
                        time.sleep(1)
                        st.rerun()

                with t_ex:
                    st.error("Isso apagará este registro permanentemente.")
                    if st.button("Confirmar Exclusão Definitiva"):
                        df_new = df_agenda[df_agenda['ID'].astype(str) != str(sel_row['ID'])].drop(columns=['LINHA'], errors='ignore')
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_new)
                        st.cache_data.clear()
                        st.success("Removido!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("Nenhum agendamento encontrado.")
    else:
        st.warning("Agenda vazia.")
