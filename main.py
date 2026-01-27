import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
import pytz

# 1. Configuração da Página
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# 2. Conexão e Fuso
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

# --- ESTADO DE SESSÃO (Login) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_nome' not in st.session_state:
    st.session_state.usuario_nome = ""

# --- FUNÇÕES DE APOIO ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Minha_Agenda')
    return output.getvalue()

def gerar_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Agenda Marata - Supervisor: {st.session_state.usuario_nome}", ln=True, align='C')
    pdf.ln(5)
    larguras = [35, 22, 35, 70, 46, 30] 
    pdf.set_font("Arial", 'B', 8)
    for i, col in enumerate(df.columns):
        pdf.cell(larguras[i], 8, str(col), border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 8)
    for _, row in df.iterrows():
        for i, item in enumerate(row):
            pdf.cell(larguras[i], 8, str(item)[:40], border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=10)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        for df in [df_b, df_j, df_a, df_u]:
            df.columns = [str(c).strip() for c in df.columns]
        
        df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except: return None, None, None, None

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- TELA DE ACESSO ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.title("☕ MARATÁ")
        st.markdown("### 🔒 Acesso do Supervisor")
        tab1, tab2 = st.tabs(["Entrar", "Cadastrar Novo"])
        
        with tab1:
            u = st.text_input("Usuário (Nome Identêntico ao da Planilha)")
            s = st.text_input("Senha", type="password")
            if st.button("Acessar Minha Agenda", use_container_width=True):
                if df_usuarios is not None and not df_usuarios.empty:
                    match = df_usuarios[(df_usuarios['USUARIO'] == u) & (df_usuarios['SENHA'].astype(str) == s)]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = u
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Erro ao carregar usuários. Verifique a aba 'USUARIOS' na planilha.")
        
        with tab2:
            st.info("Atenção: O nome de usuário deve ser o mesmo que consta na sua Região de Vendas.")
            nu = st.text_input("Definir Nome de Usuário")
            ns = st.text_input("Definir Senha", type="password")
            if st.button("Confirmar Cadastro", use_container_width=True):
                if nu and ns:
                    novo_u = pd.DataFrame([{"USUARIO": nu, "SENHA": ns}])
                    df_u_f = pd.concat([df_usuarios, novo_u], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_u_f)
                    st.success("Cadastro realizado com sucesso! Vá para a aba 'Entrar'.")
                    st.cache_data.clear()
    st.stop()

# --- ÁREA LOGADA ---
with st.sidebar:
    st.subheader("☕ Gestão Maratá")
    st.write(f"Conectado: **{st.session_state.usuario_nome}**")
    st.markdown("---")
    menu = st.selectbox("Menu Principal", ["Novo Agendamento", "Minha Agenda"])
    if st.button("🚪 Sair do Sistema"):
        st.session_state.autenticado = False
        st.rerun()

# 1. NOVO AGENDAMENTO
if menu == "Novo Agendamento":
    st.header(f"📋 Agendar Visita - {st.session_state.usuario_nome}")
    
    # Filtro automático pelo nome do supervisor logado
    clientes_sup = df_base[df_base['Região de vendas'] == st.session_state.usuario_nome]
    
    if clientes_sup.empty:
        st.warning(f"Atenção: Não encontramos clientes para o supervisor '{st.session_state.usuario_nome}'.")
    else:
        lista_c = sorted(clientes_sup.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)
        
        if cliente_sel != "Selecione...":
            with st.form("f_novo"):
                data_v = st.date_input("Data da Visita:", datetime.now(fuso_br))
                if st.form_submit_button("💾 SALVAR AGENDAMENTO"):
                    cod_c, nom_c = cliente_sel.split(" - ", 1)
                    agora = datetime.now(fuso_br)
                    novo_id = agora.strftime("%Y%m%d%H%M%S")
                    nova_linha = pd.DataFrame([{
                        "ID": novo_id, 
                        "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), 
                        "DATA": data_v.strftime("%d/%m/%Y"), 
                        "SUPERVISOR": st.session_state.usuario_nome, 
                        "CÓDIGO CLIENTE": cod_c, 
                        "CLIENTE": nom_c, 
                        "JUSTIFICATIVA": "-", 
                        "STATUS": "Planejado (X)"
                    }])
                    df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear()
                    st.success("Agendamento salvo!")
                    st.rerun()

# 2. MINHA AGENDA
elif menu == "Minha Agenda":
    st.header(f"🔍 Minha Agenda - {st.session_state.usuario_nome}")
    
    # Filtro de exibição
    df_f = df_agenda[df_agenda['SUPERVISOR'] == st.session_state.usuario_nome].copy()
    
    if df_f.empty:
        st.info("Você ainda não registrou nenhum agendamento.")
    else:
        # Exportação
        df_export = df_f[['REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']]
        c1, c2, _ = st.columns([1, 1, 2])
        with c1: st.download_button("📥 Excel", data=converter_para_excel(df_export), file_name="agenda.xlsx", use_container_width=True)
        with c2: st.download_button("📄 PDF", data=gerar_pdf(df_export), file_name="agenda.pdf", use_container_width=True)

        # Editor de Tabela
        df_f["EDITAR"] = False
        cols_v = ['EDITAR', 'DATA', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        edicao = st.data_editor(df_f[cols_v], column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                                 disabled=[c for c in cols_v if c != "EDITAR"], hide_index=True, use_container_width=True)

        marcadas = edicao[edicao["EDITAR"] == True]
        if not marcadas.empty:
            idx = marcadas.index[0]
            row = df_f.loc[idx]
            id_s = row['ID']
            
            with st.form("edit_form"):
                st.write(f"**Cliente:** {row['CLIENTE']}")
                st_list = ["Planejado (X)", "Realizado", "Reagendado"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                
                n_st = st.radio("Status:", st_list, index=st_list.index(row['STATUS']) if row['STATUS'] in st_list else 0, horizontal=True)
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(row['JUSTIFICATIVA']) if row['JUSTIFICATIVA'] in ju_list else 0)
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.form_submit_button("✅ SALVAR", use_container_width=True):
                        df_agenda.loc[df_agenda['ID'] == id_s, ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                        st.cache_data.clear()
                        st.rerun()
                with b2:
                    if st.form_submit_button("🗑️ EXCLUIR", use_container_width=True):
                        df_novo = df_agenda[df_agenda['ID'] != id_s].drop(columns=['LINHA'], errors='ignore')
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_novo)
                        st.cache_data.clear()
                        st.rerun()
