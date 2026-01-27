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
NOME_ADMIN = "SEU NOME AQUI" # <--- COLOQUE SEU NOME EXATO AQUI PARA SER ADMIN

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
    larguras = [35, 22, 35, 70, 46, 30] 
    pdf.set_font("Arial", 'B', 8)
    for i, col in enumerate(df.columns):
        pdf.cell(larguras[i], 8, str(col), border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 8)
    for index, row in df.iterrows():
        for i, item in enumerate(row):
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
        
        for df in [df_b, df_j, df_a, df_u]:
            df.columns = [str(c).strip() for c in df.columns]
            
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
        df_a['LINHA'] = df_a.index + 2
        
        # Formatação de códigos
        for df in [df_b, df_a]:
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
                df[col] = df[col].replace('0', '')
        
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None, None, None

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- SISTEMA DE LOGIN ---
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""

if not st.session_state.logado:
    st.title("☕ Acesso Gestão Maratá")
    aba_login, aba_cad = st.tabs(["Login", "Novo Cadastro"])
    
    with aba_login:
        with st.form("form_login"):
            user_input = st.text_input("Digite seu nome completo (conforme planilha):").strip().upper()
            if st.form_submit_button("Entrar"):
                if user_input in df_usuarios['NOME'].str.upper().values:
                    st.session_state.logado = True
                    st.session_state.usuario = user_input
                    st.rerun()
                else:
                    st.error("Usuário não encontrado. Verifique o nome ou cadastre-se.")

    with aba_cad:
        with st.form("form_cadastro"):
            novo_nome = st.text_input("Nome Completo:").strip().upper()
            if st.form_submit_button("Cadastrar"):
                if novo_nome and novo_nome not in df_usuarios['NOME'].str.upper().values:
                    novo_user_df = pd.concat([df_usuarios, pd.DataFrame([{"NOME": novo_nome}])], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=novo_user_df)
                    st.success("Cadastro realizado! Agora faça o login.")
                    st.cache_data.clear()
                else:
                    st.warning("Nome inválido ou já cadastrado.")
    st.stop()

# --- LOGADO COMO... ---
user_atual = st.session_state.usuario
is_admin = (user_atual == NOME_ADMIN.upper())
label_user = "ADMINISTRADOR" if is_admin else user_atual

# --- BARRA LATERAL ---
with st.sidebar:
    try:
        st.image("pngmarata.png", width=150)
    except:
        st.warning("Logo não encontrada.")
    
    st.write(f"👤 **{label_user}**")
    menu = st.selectbox("Menu Principal", ["Novo Agendamento", "Ver/Editar Minha Agenda"])
    
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.markdown("---")
    if is_admin:
        st.subheader("🗑️ Limpeza em Massa (Admin)")
        if df_agenda is not None and not df_agenda.empty:
            lista_supervisores = sorted(df_agenda['SUPERVISOR'].unique())
            sup_para_limpar = st.selectbox("Limpar toda agenda de:", ["Selecione..."] + lista_supervisores)
            if sup_para_limpar != "Selecione...":
                if st.button(f"⚠️ APAGAR TUDO: {sup_para_limpar}", use_container_width=True):
                    df_restante = df_agenda[df_agenda['SUPERVISOR'] != sup_para_limpar].drop(columns=['LINHA'], errors='ignore')
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_restante)
                    st.cache_data.clear()
                    st.rerun()

# --- PÁGINA: NOVO AGENDAMENTO ---
if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    if df_base is not None:
        # Se for admin, escolhe qualquer um. Se não, trava no nome dele.
        if is_admin:
            supervisores = sorted([s for s in df_base['Região de vendas'].unique() if str(s).strip() and str(s) != 'nan'])
            sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)
        else:
            sup_sel = user_atual
            st.info(f"Agendando como: {user_atual}")

        if sup_sel != "Selecione...":
            clientes_f = df_base[df_base['Região de vendas'] == sup_sel]
            lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)
            
            if cliente_sel != "Selecione...":
                qtd_visitas = st.number_input("Quantas visitas deseja agendar?", min_value=1, max_value=4, value=1)
                
                with st.form("form_novo"):
                    st.markdown(f"**Datas para as {qtd_visitas} visita(s):**")
                    datas_selecionadas = []
                    cols_datas = st.columns(qtd_visitas)
                    for i in range(qtd_visitas):
                        with cols_datas[i]:
                            d = st.date_input(f"Data {i+1}:", datetime.now(fuso_br), key=f"data_v_{i}")
                            datas_selecionadas.append(d)
                    
                    if st.form_submit_button("💾 CONFIRMAR TODOS"):
                        cod_c, nom_c = cliente_sel.split(" - ", 1)
                        agora = datetime.now(fuso_br)
                        agora_str = agora.strftime("%d/%m/%Y %H:%M")
                        
                        novas_linhas = []
                        for i, data_v in enumerate(datas_selecionadas):
                            novo_id = (agora + timedelta(seconds=i)).strftime("%Y%m%d%H%M%S") + str(i)
                            novas_linhas.append({
                                "ID": novo_id, "REGISTRO": agora_str, "DATA": data_v.strftime("%d/%m/%Y"), 
                                "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, 
                                "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)"
                            })
                        
                        df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), pd.DataFrame(novas_linhas)], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                        st.cache_data.clear()
                        st.success(f"✅ Agendado com sucesso!")
                        time.sleep(1)
                        st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    if df_agenda is not None and not df_agenda.empty:
        # Filtro de visualização
        if is_admin:
            f_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + sorted(df_agenda['SUPERVISOR'].unique()))
            df_f = df_agenda.copy()
            if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]
        else:
            df_f = df_agenda[df_agenda['SUPERVISOR'] == user_atual].copy()
            st.info(f"Mostrando apenas visitas de: {user_atual}")

        # Exportação
        df_exportar = df_f[['REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']]
        c_exp1, c_exp2, _ = st.columns([1, 1, 2])
        with c_exp1:
            st.download_button("📥 Excel", data=converter_para_excel(df_exportar), file_name="agenda_marata.xlsx", use_container_width=True)
        with c_exp2:
            try: st.download_button("📄 PDF", data=gerar_pdf(df_exportar), file_name="agenda_marata.pdf", use_container_width=True)
            except: st.error("Erro no PDF")

        # Tabela de Edição
        df_f["EDITAR"] = False 
        cols_v = ['EDITAR', 'REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        edicao = st.data_editor(
            df_f[cols_v],
            column_config={"EDITAR": st.column_config.CheckboxColumn("📝", default=False)},
            disabled=[c for c in cols_v if c != "EDITAR"],
            hide_index=True,
            use_container_width=True,
            key="editor_final_v11"
        )

        linhas_marcadas = edicao[edicao["EDITAR"] == True]
        if not linhas_marcadas.empty:
            idx = linhas_marcadas.index[0]
            dados = df_f.loc[idx]
            id_s = dados['ID']
            st.markdown("---")
            st.subheader(f"⚙️ Opções para: {dados['CLIENTE']}")
            
            st_list = ["Planejado (X)", "Realizado", "Reagendado"]
            ju_list = list(df_just.iloc[:, 0].dropna().unique())
            if "OUTRO" not in ju_list: ju_list.append("OUTRO")
            
            col_esq, col_dir = st.columns(2)
            with col_esq:
                n_st = st.radio("Status:", st_list, index=st_list.index(dados['STATUS']) if dados['STATUS'] in st_list else 0)
            with col_dir:
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(dados['JUSTIFICATIVA']) if dados['JUSTIFICATIVA'] in ju_list else 0)
                motivo_outro = st.text_input("Especifique o motivo:", placeholder="Escreva aqui...") if n_ju == "OUTRO" else ""

            with st.form("form_salvamento"):
                b_at, b_ex = st.columns(2)
                with b_at:
                    if st.form_submit_button("✅ SALVAR ALTERAÇÕES", use_container_width=True):
                        j_salvar = motivo_outro if n_ju == "OUTRO" and motivo_outro.strip() != "" else n_ju
                        df_agenda.loc[df_agenda['ID'] == id_s, ['STATUS', 'JUSTIFICATIVA']] = [n_st, j_salvar]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                        st.cache_data.clear()
                        st.success("Salvo!")
                        st.rerun()
                with b_ex:
                    if st.form_submit_button("🗑️ EXCLUIR", use_container_width=True):
                        df_novo = df_agenda[df_agenda['ID'] != id_s].drop(columns=['LINHA'], errors='ignore')
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_novo)
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("Agenda vazia.")
