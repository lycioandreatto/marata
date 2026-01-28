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
        df.to_excel(writer, index=False, sheet_name='Agenda')
    return output.getvalue()

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

if is_admin:
    label_display = "ADMINISTRADOR"
elif is_diretoria:
    label_display = f"DIRETORIA {user_atual}"
elif is_analista:
    label_display = f"ANALISTA {user_atual}"
else:
    label_display = f"SUPERVISOR {user_atual}"

# --- BARRA LATERAL ---
with st.sidebar:
    try: st.image("pngmarata.png", width=150)
    except: st.warning("Logo não encontrada.")
    st.markdown(f"👤 **{label_display}**")
    menu = st.selectbox("Menu Principal", ["Novo Agendamento", "Ver/Editar Minha Agenda"])
    if st.button("Sair"):
        st.session_state.logado = False
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

# --- PÁGINA: NOVO AGENDAMENTO ---
if menu == "Novo Agendamento":
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
            # Filtrar clientes do supervisor na base
            clientes_f = df_base[df_base[col_rv_base] == sup_sel]
            
            # --- LÓGICA DE CONTADORES E FILTRO DE EXIBIÇÃO ---
            # Pegar códigos de clientes que já estão na Agenda para este supervisor
            codigos_agendados = df_agenda[df_agenda['SUPERVISOR'] == sup_sel]['CÓDIGO CLIENTE'].unique()
            
            # Filtrar a base para mostrar apenas quem NÃO está agendado
            clientes_pendentes = clientes_f[~clientes_f['Cliente'].isin(codigos_agendados)]
            
            # Mostrar métricas (Contadores)
            m1, m2, m3 = st.columns(3)
            m1.metric("Total na Base", len(clientes_f))
            m2.metric("Já Agendados", len(codigos_agendados))
            m3.metric("Faltando", len(clientes_pendentes))
            
            # BUSCA AUTOMÁTICA DA ANALISTA VINCULADA
            analista_vinc = NOME_ANALISTA
            if col_ana_base in clientes_f.columns:
                val_analista = clientes_f[col_ana_base].iloc[0]
                if str(val_analista).strip() and str(val_analista).lower() != 'nan':
                    analista_vinc = str(val_analista).upper()

            # Lista apenas os clientes que FALTAM agendar
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
                                    "ID": nid, "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), "DATA": dt.strftime("%d/%m/%Y"),
                                    "ANALISTA": analista_vinc, "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, 
                                    "CLIENTE": nom_c, "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)"
                                })
                            df_final_a = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas_linhas)], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                            st.cache_data.clear()
                            st.success(f"✅ {qtd_visitas} visita(s) salva(s)!")
                            time.sleep(1)
                            st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
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
        df_exp = df_f[['REGISTRO', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']]
        
        c1, c2, _ = st.columns([1,1,2])
        with c1: st.download_button("📥 Excel", data=converter_para_excel(df_exp), file_name="agenda.xlsx")
        with c2: 
            try: st.download_button("📄 PDF", data=gerar_pdf(df_exp), file_name="agenda.pdf")
            except: st.error("Erro ao gerar PDF")

        df_f["EDITAR"] = False
        cols_v = ['EDITAR', 'REGISTRO', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        edicao = st.data_editor(df_f[cols_v], key="edit_v12", hide_index=True, use_container_width=True,
                                 column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                                 disabled=[c for c in cols_v if c != "EDITAR"])

        marcados = edicao[edicao["EDITAR"] == True]
        if not marcados.empty:
            sel_row = df_f.loc[marcados.index[0]]
            st.markdown("---")
            st.subheader(f"Editar: {sel_row['CLIENTE']}")
            st_list = ["Planejado (X)", "Realizado", "Reagendado"]
            ju_list = list(df_just.iloc[:, 0].dropna().unique())
            if "OUTRO" not in ju_list: ju_list.append("OUTRO")
            
            col1, col2 = st.columns(2)
            with col1: n_st = st.radio("Status:", st_list, index=st_list.index(sel_row['STATUS']) if sel_row['STATUS'] in st_list else 0)
            with col2:
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(sel_row['JUSTIFICATIVA']) if sel_row['JUSTIFICATIVA'] in ju_list else 0)
                mot_outro = st.text_input("Qual o motivo?") if n_ju == "OUTRO" else ""

            with st.form("save_form"):
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 SALVAR"):
                    final_j = mot_outro if n_ju == "OUTRO" else n_ju
                    df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['STATUS', 'JUSTIFICATIVA']] = [n_st, final_j]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
                if b2.form_submit_button("🗑️ EXCLUIR"):
                    df_novo_a = df_agenda[df_agenda['ID'] != sel_row['ID']].drop(columns=['LINHA'], errors='ignore')
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_novo_a)
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.info("Nenhum registro encontrado.")
