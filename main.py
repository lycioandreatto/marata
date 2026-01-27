import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF

# 1. Configuração da Página
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# 2. Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

# --- FUNÇÕES DE EXPORTAÇÃO ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Agenda')
    return output.getvalue()

def gerar_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Agenda de Visitas Marata - {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 10)
    col_width = 45 
    for col in df.columns:
        pdf.cell(col_width, 10, str(col), border=1, align='C')
    pdf.ln()
    
    # Dados
    pdf.set_font("Arial", '', 9)
    for index, row in df.iterrows():
        for item in row:
            pdf.cell(col_width, 10, str(item)[:25], border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS COM CACHE ---
@st.cache_data(ttl=600)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        
        # Limpeza de nomes de colunas
        df_b.columns = [str(c).strip() for c in df_b.columns]
        df_j.columns = [str(c).strip() for c in df_j.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
        
        if 'ID' in df_a.columns:
            df_a['ID'] = df_a['ID'].astype(str)
            
        return df_b, df_j, df_a
    except Exception:
        return None, None, None

df_base, df_just, df_agenda = carregar_dados()

if df_base is None:
    st.error("🚨 Limite de acessos atingido. Aguarde 30 segundos e atualize a pagina.")
    st.stop()

# --- INTERFACE ---
st.sidebar.image("https://marata.com.br/wp-content/uploads/2021/05/logo-marata.png", width=120)
menu = st.sidebar.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

# --- NOVO AGENDAMENTO ---
if menu == "Novo Agendamento":
    st.header("📋 Novo Agendamento")
    col_sup_nome = 'Região de vendas'
    
    supervisores = sorted([s for s in df_base[col_sup_nome].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        clientes_f = df_base[df_base[col_sup_nome] == sup_sel]
        lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        
        st.info("💡 Digite o nome ou codigo para pesquisar.")
        cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)

        if cliente_sel != "Selecione...":
            opcoes_j = df_just.iloc[:, 0].dropna().unique()
            with st.form("form_novo"):
                col1, col2 = st.columns(2)
                with col1:
                    status = st.radio("Status:", ("Planejado (X)", "Realizado", "Reagendado"))
                    data_v = st.date_input("Data da Visita:", datetime.now())
                with col2:
                    just_sel = st.selectbox("Justificativa:", list(opcoes_j))
                
                if st.form_submit_button("💾 SALVAR"):
                    cod_c, nom_c = cliente_sel.split(" - ", 1)
                    novo_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    nova_linha = pd.DataFrame([{"ID": novo_id, "DATA": data_v.strftime("%d/%m/%Y"), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": just_sel, "STATUS": status}])
                    
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Agendado!")
                    st.rerun()

# --- VISUALIZAÇÃO E EDIÇÃO ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    
    if not df_agenda.empty:
        # Ordenação Cronológica
        df_agenda['DATA_OBJ'] = pd.to_datetime(df_agenda['DATA'], format='%d/%m/%Y', errors='coerce')
        df_agenda = df_agenda.sort_values(by='DATA_OBJ', ascending=True)

        supervisores_a = sorted(df_agenda['SUPERVISOR'].unique())
        f_sup = st.selectbox("Filtrar Supervisor:", ["Todos"] + supervisores_a)
        
        df_f = df_agenda.copy()
        if f_sup != "Todos":
            df_f = df_f[df_f['SUPERVISOR'] == f_sup]

        cols_v = [c for c in df_f.columns if c not in ['ID', 'DATA_OBJ']]
        df_export = df_f[cols_v]

        # --- BOTÕES DE DOWNLOAD ---
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            st.download_button("📥 Excel", data=converter_para_excel(df_export), file_name="agenda_marata.xlsx")
        with c2:
            try:
                st.download_button("📄 PDF", data=gerar_pdf(df_export), file_name="agenda_marata.pdf")
            except:
                st.warning("Erro PDF (caracteres)")

        st.dataframe(df_export, use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Atualizar Status")
        dict_l = {f"{row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_f.iterrows()}
        edit_sel = st.selectbox("Selecione a visita para editar:", ["Selecione..."] + list(dict_l.keys()))

        if edit_sel != "Selecione...":
            id_s = dict_l[edit_sel]
            match = df_agenda[df_agenda['ID'] == id_s]
            if not match.empty:
                dv = match.iloc[0]
                with st.form("form_edit"):
                    st_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    idx_s = st_list.index(dv['STATUS']) if dv['STATUS'] in st_list else 0
                    ju_list = list(df_just.iloc[:, 0].dropna().unique())
                    idx_j = ju_list.index(dv['JUSTIFICATIVA']) if dv['JUSTIFICATIVA'] in ju_list else 0

                    n_st = st.radio("Novo Status:", st_list, index=idx_s, horizontal=True)
                    n_ju = st.selectbox("Nova Justificativa:", ju_list, index=idx_j)

                    if st.form_submit_button("✅ ATUALIZAR"):
                        df_save = df_agenda.drop(columns=['DATA_OBJ'])
                        df_save.loc[df_save['ID'] == id_s, 'STATUS'] = n_st
                        df_save.loc[df_save['ID'] == id_s, 'JUSTIFICATIVA'] = n_ju
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save)
                        st.cache_data.clear()
                        st.success("✅ Atualizado!")
                        st.rerun()
    else:
        st.info("Agenda vazia.")
