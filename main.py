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

    largura_cliente, largura_supervisor, largura_agendado, largura_data, largura_justificativa, largura_registro, largura_cidade = 60, 30, 30, 18, 50, 25, 40
    
    especiais = []
    col_map = {str(c).upper(): c for c in cols}
    for k in ["CLIENTE", "SUPERVISOR", "AGENDADO POR", "DATA", "JUSTIFICATIVA", "REGISTRO", "CIDADE"]:
        if k in col_map: especiais.append(k)
    
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
        w = largura_cliente if c_up == "CLIENTE" else largura_supervisor if c_up == "SUPERVISOR" else largura_agendado if c_up == "AGENDADO POR" else largura_data if c_up == "DATA" else largura_justificativa if c_up == "JUSTIFICATIVA" else largura_registro if c_up == "REGISTRO" else largura_cidade if c_up == "CIDADE" else largura_padrao
        pdf.cell(w, 6, str(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', tamanho_fonte_dados) 
    for index, row in df_pdf.iterrows():
        for i, item in enumerate(row):
            col_name = str(cols[i]).upper()
            w, limit = (largura_cliente, 50) if col_name == "CLIENTE" else (largura_supervisor, 30) if col_name == "SUPERVISOR" else (largura_agendado, 30) if col_name == "AGENDADO POR" else (largura_data, 12) if col_name == "DATA" else (largura_justificativa, 60) if col_name == "JUSTIFICATIVA" else (largura_registro, 20) if col_name == "REGISTRO" else (largura_cidade, 35) if col_name == "CIDADE" else (largura_padrao, limite_texto)
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
                    else: st.error("Usuário ou Senha incorretos.")
                else: st.error("Erro na base de usuários.")
    with tab_cadastro:
        with st.form("cad_form"):
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

# --- PERFIL DO USUÁRIO ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
is_analista = (user_atual == NOME_ANALISTA.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

if is_admin: label_display, user_icon, border_color = "ADMINISTRADOR", "👑", "#FFD700"
elif is_diretoria: label_display, user_icon, border_color = f"DIRETORIA {user_atual}", "📈", "#1E90FF"
elif is_analista: label_display, user_icon, border_color = f"ANALISTA {user_atual}", "🔬", "#9370DB"
else: label_display, user_icon, border_color = f"SUPERVISOR {user_atual}", "👤", "#ff4b4b"

# --- LÓGICA DE NOTIFICAÇÃO DE ATRASO (16:00) ---
tem_atraso = False
agora_br = datetime.now(fuso_br)
hoje_str = agora_br.strftime("%d/%m/%Y")

if df_agenda is not None and not df_agenda.empty:
    df_hoje = df_agenda[(df_agenda['DATA'] == hoje_str) & (df_agenda['STATUS'] != "Realizado")]
    if not (is_admin or is_diretoria or is_analista):
        df_hoje = df_hoje[df_hoje['SUPERVISOR'] == user_atual]
    
    if not df_hoje.empty and agora_br.hour >= 16:
        tem_atraso = True

# --- BARRA LATERAL ---
with st.sidebar:
    try: st.image("pngmarata", width=150)
    except: st.warning("Logo não encontrada.")
    
    st.markdown(f'<div class="user-card" style="border-left: 5px solid {border_color};"><div class="user-card-icon">{user_icon}</div><div class="user-card-text">{label_display}</div></div>', unsafe_allow_html=True)
    
    label_dia = "📅 Agendamentos do Dia"
    if tem_atraso: label_dia += " 🔔"
    
    opcoes_menu = [label_dia, "📋 Novo Agendamento", "🔍 Ver/Editar Minha Agenda"]
    if is_admin or is_analista or is_diretoria: opcoes_menu.append("📊 Dashboard de Controle")
    menu = st.selectbox("Menu Principal", opcoes_menu)
    
    if st.button("Sair"):
        if "user_marata" in cookies: del cookies["user_marata"]
        cookies.save()
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
                st.cache_data.clear(); st.rerun()
        else:
            if st.button(f"⚠️ APAGAR TODA MINHA AGENDA"):
                df_rest = df_agenda[df_agenda['SUPERVISOR'] != user_atual].drop(columns=['LINHA'], errors='ignore')
                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_rest)
                st.cache_data.clear(); st.rerun()

st.markdown("<h4 style='text-align: center; color: white; margin-top: -50px;'>SISTEMA DE CONTROLE DE AGENDAMENTOS (SCA) - MARATÁ</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- PÁGINA: AGENDAMENTOS DO DIA ---
if label_dia in menu:
    st.header("📅 Agendamentos do Dia")
    if tem_atraso:
        st.error("🚨 Atenção: Existem visitas pendentes após as 16h!")

    if df_agenda is not None and not df_agenda.empty:
        df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
        if not (is_admin or is_diretoria):
            df_dia = df_dia[df_dia['ANALISTA' if is_analista else 'SUPERVISOR'].str.upper() == user_atual]

        st.columns([1, 3])[0].metric("Visitas Hoje", len(df_dia))
        if not df_dia.empty:
            if df_base is not None:
                col_local_base = next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
                df_dia = pd.merge(df_dia, df_base[['Cliente', col_local_base]], left_on='CÓDIGO CLIENTE', right_on='Cliente', how='left').drop(columns=['Cliente_y'], errors='ignore').rename(columns={col_local_base: 'CIDADE'})

            df_dia["EDITAR"] = False
            cols_v = ['EDITAR', 'DATA', 'SUPERVISOR', 'CLIENTE', 'CIDADE', 'JUSTIFICATIVA', 'STATUS', 'AGENDADO POR']
            edicao_dia = st.data_editor(df_dia[cols_v], key="edit_dia", hide_index=True, use_container_width=True, column_config={"EDITAR": st.column_config.CheckboxColumn("📝")}, disabled=[c for c in cols_v if c != "EDITAR"])

            marcados = edicao_dia[edicao_dia["EDITAR"] == True]
            if not marcados.empty:
                sel_row = df_dia.iloc[marcados.index[0]]
                st.subheader(f"Atualizar: {sel_row['CLIENTE']}")
                st_list, ju_list = ["Planejado (X)", "Realizado", "Reagendado"], list(df_just.iloc[:, 0].dropna().unique()) + ["OUTRO"]
                c1, c2 = st.columns(2)
                with c1: n_st = st.radio("Status:", st_list, index=st_list.index(sel_row['STATUS']) if sel_row['STATUS'] in st_list else 0)
                with c2: n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(sel_row['JUSTIFICATIVA']) if sel_row['JUSTIFICATIVA'] in ju_list else 0)
                if st.button("💾 ATUALIZAR STATUS"):
                    df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear(); st.success("Atualizado!"); time.sleep(1); st.rerun()
        else: st.info(f"Sem agendamentos para hoje.")

# --- PÁGINA: DASHBOARD ---
elif menu == "📊 Dashboard de Controle":
    st.header("📊 Resumo de Engajamento")
    if df_base is not None and df_agenda is not None:
        col_ana_base, col_rv_base, col_local_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'Analista'), next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas'), next((c for c in df_base.columns if c.upper() == 'LOCAL'), 'Local')
        f_c1, f_c2 = st.columns(2)
        df_base_f = df_base.copy()
        with f_c1:
            if is_admin or is_diretoria:
                ana_sel = st.selectbox("Analista:", ["Todos"] + sorted(df_base[col_ana_base].dropna().unique()))
                if ana_sel != "Todos": df_base_f = df_base_f[df_base_f[col_ana_base] == ana_sel]
            else: df_base_f = df_base_f[df_base_f[col_ana_base].str.upper() == user_atual]
        with f_c2:
            sup_sel = st.selectbox("Supervisor:", ["Todos"] + sorted(df_base_f[col_rv_base].dropna().unique()))
            if sup_sel != "Todos": df_base_f = df_base_f[df_base_f[col_rv_base] == sup_sel]

        res_b = df_base_f.groupby(col_rv_base).size().reset_index(name='Total na Base')
        res_a = df_agenda[df_agenda['CÓDIGO CLIENTE'].isin(df_base_f['Cliente'])].groupby('SUPERVISOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Agendados')
        df_dash = pd.merge(res_b, res_a, left_on=col_rv_base, right_on='SUPERVISOR', how='left').fillna(0)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Agendados']
        st.dataframe(df_dash, use_container_width=True, hide_index=True)

# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    if df_base is not None:
        col_rv_base = next((c for c in df_base.columns if c.upper() == 'REGIÃO DE VENDAS'), 'Região de vendas')
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'Analista')
        sup_sel = st.selectbox("Supervisor:", sorted(df_base[col_rv_base].unique())) if (is_admin or is_diretoria or is_analista) else user_atual
        
        clientes_f = df_base[df_base[col_rv_base] == sup_sel]
        agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
        clientes_p = clientes_f[~clientes_f['Cliente'].isin(agendados)]
        
        st.metric("Clientes Faltando", len(clientes_p))
        lista_c = sorted(clientes_p.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        
        if lista_c:
            cliente_sel = st.selectbox("Selecione Cliente:", ["Selecione..."] + lista_c)
            if cliente_sel != "Selecione...":
                qtd_v = st.number_input("Visitas:", 1, 4, 1)
                with st.form("f_v"):
                    cols = st.columns(qtd_v)
                    datas = [cols[i].date_input(f"Data {i+1}", datetime.now(fuso_br), key=f"dt_{i}") for i in range(qtd_v)]
                    if st.form_submit_button("💾 SALVAR AGENDAMENTOS"):
                        cod_c, nom_c = cliente_sel.split(" - ", 1)
                        agora = datetime.now(fuso_br)
                        novas = []
                        for i, dt in enumerate(datas):
                            novas.append({"ID": agora.strftime("%Y%m%d%H%M%S")+str(i), "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), "DATA": dt.strftime("%d/%m/%Y"), "ANALISTA": str(clientes_f[col_ana_base].iloc[0]).upper(), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)", "AGENDADO POR": user_atual})
                        df_final_a = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas)], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                        
                        # --- ALERTA POP-UP SOLICITADO ---
                        st.toast(f'✅ foi feito um novo agendamento para {nom_c}!', icon='🚀')
                        
                        st.cache_data.clear(); time.sleep(1); st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    if df_agenda is not None and not df_agenda.empty:
        df_f = df_agenda if (is_admin or is_diretoria) else df_agenda[df_agenda['SUPERVISOR' if not is_analista else 'ANALISTA'].str.upper() == user_atual]
        st.dataframe(df_f.sort_values(by="REGISTRO", ascending=False), use_container_width=True, hide_index=True)
