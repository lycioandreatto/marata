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
    
    # Larguras: DATA(25), SUPERVISOR(40), COD(35), CLIENTE(90), JUSTIF(55), STATUS(30)
    larguras = [25, 40, 35, 90, 55, 30] 
    
    pdf.set_font("Arial", 'B', 9)
    for i, col in enumerate(df.columns):
        pdf.cell(larguras[i], 10, str(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    for index, row in df.iterrows():
        for i, item in enumerate(row):
            texto = str(item)
            if i == 3: limite = 55 
            elif i == 4: limite = 35 
            elif i == 1: limite = 25 
            else: limite = 20
            pdf.cell(larguras[i], 10, texto[:limite], border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS COM CACHE ---
@st.cache_data(ttl=600)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        
        for df in [df_b, df_j, df_a]:
            df.columns = [str(c).strip() for c in df.columns]
            cols_codigo = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_codigo:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
                df[col] = df[col].replace('0', '')

        if 'ID' in df_a.columns:
            df_a['ID'] = df_a['ID'].astype(str)
            
        return df_b, df_j, df_a
    except Exception:
        return None, None, None

df_base, df_just, df_agenda = carregar_dados()

if df_base is None:
    st.error("🚨 Limite de acessos atingido. Aguarde 30 segundos.")
    st.stop()

# --- INTERFACE ---
st.sidebar.image("https://marata.com.br/wp-content/uploads/2021/05/logo-marata.png", width=120)
menu = st.sidebar.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

# --- NOVO AGENDAMENTO (Simplificado) ---
if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    col_sup_nome = 'Região de vendas'
    
    supervisores = sorted([s for s in df_base[col_sup_nome].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)

    if sup_sel != "Selecione...":
        clientes_f = df_base[df_base[col_sup_nome] == sup_sel]
        lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        
        cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)

        if cliente_sel != "Selecione...":
            with st.form("form_novo"):
                st.write(f"Agendando visita para: **{cliente_sel}**")
                data_v = st.date_input("Data da Visita:", datetime.now())
                
                if st.form_submit_button("💾 CONFIRMAR AGENDAMENTO"):
                    cod_c, nom_c = cliente_sel.split(" - ", 1)
                    novo_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    
                    # Salva com Status Padrão e Justificativa Vazia
                    nova_linha = pd.DataFrame([{
                        "ID": novo_id, 
                        "DATA": data_v.strftime("%d/%m/%Y"), 
                        "SUPERVISOR": sup_sel, 
                        "CÓDIGO CLIENTE": cod_c, 
                        "CLIENTE": nom_c, 
                        "JUSTIFICATIVA": "-", 
                        "STATUS": "Planejado (X)"
                    }])
                    
                    df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Visita agendada como 'Planejada'!")
                    st.rerun()

# --- VISUALIZAÇÃO E EDIÇÃO ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    
    if not df_agenda.empty:
        df_agenda['DATA_OBJ'] = pd.to_datetime(df_agenda['DATA'], format='%d/%m/%Y', errors='coerce')
        df_agenda = df_agenda.sort_values(by='DATA_OBJ', ascending=True)

        supervisores_a = sorted(df_agenda['SUPERVISOR'].unique())
        f_sup = st.selectbox("Filtrar Supervisor:", ["Todos"] + supervisores_a)
        
        df_f = df_agenda.copy()
        if f_sup != "Todos":
            df_f = df_f[df_f['SUPERVISOR'] == f_sup]

        cols_v = [c for c in df_f.columns if c not in ['ID', 'DATA_OBJ']]
        df_export = df_f[cols_v]

        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            st.download_button("📥 Excel", data=converter_para_excel(df_export), file_name="agenda_marata.xlsx")
        with c2:
            try:
                st.download_button("📄 PDF", data=gerar_pdf(df_export), file_name="agenda_marata.pdf")
            except:
                st.warning("Erro ao gerar PDF.")

        st.dataframe(df_export, use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Atualizar Visita (Status e Justificativa)")
        dict_l = {f"{row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_f.iterrows()}
        edit_sel = st.selectbox("Selecione a visita realizada:", ["Selecione..."] + list(dict_l.keys()))

        if edit_sel != "Selecione...":
            id_s = dict_l[edit_sel]
            match = df_agenda[df_agenda['ID'] == id_s]
            if not match.empty:
                dv = match.iloc[0]
                with st.form("form_edit"):
                    st.write(f"Atualizando: **{dv['CLIENTE']}**")
                    st_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    # Tenta encontrar o índice atual ou assume 0
                    try: idx_s = st_list.index(dv['STATUS'])
                    except: idx_s = 0
                    
                    ju_list = list(df_just.iloc[:, 0].dropna().unique())
                    try: idx_j = ju_list.index(dv['JUSTIFICATIVA'])
                    except: idx_j = 0
                    
                    n_st = st.radio("Mudar Status para:", st_list, index=idx_s, horizontal=True)
                    n_ju = st.selectbox("Selecione a Justificativa:", ju_list, index=idx_j)
                    
                    if st.form_submit_button("✅ ATUALIZAR STATUS"):
                        df_save = df_agenda.drop(columns=['DATA_OBJ'])
                        df_save.loc[df_save['ID'] == id_s, 'STATUS'] = n_st
                        df_save.loc[df_save['ID'] == id_s, 'JUSTIFICATIVA'] = n_ju
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save)
                        st.cache_data.clear()
                        st.success("✅ Status atualizado com sucesso!")
                        st.rerun()
    else:
        st.info("Agenda vazia.")
