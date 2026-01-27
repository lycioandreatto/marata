import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
import pytz

# 1. Configuração da Página
st.set_page_config(page_title="Gestão Maratá", page_icon="☕", layout="wide")

# 2. Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"

fuso_br = pytz.timezone('America/Sao_Paulo')

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
    larguras = [12, 35, 22, 35, 25, 70, 46, 30] 
    pdf.set_font("Arial", 'B', 7)
    for i, col in enumerate(df.columns):
        pdf.cell(larguras[i], 8, str(col), border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 7)
    for index, row in df.iterrows():
        for i, item in enumerate(row):
            pdf.cell(larguras[i], 8, str(item)[:40], border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        
        df_a.columns = [str(c).strip() for c in df_a.columns]
        if 'REGISTRO' not in df_a.columns:
            df_a['REGISTRO'] = "-"

        # LINHA real do Sheets
        df_a['LINHA'] = df_a.index + 2
        
        for df in [df_b, df_j, df_a]:
            df.columns = [str(c).strip() for c in df.columns]
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
                df[col] = df[col].replace('0', '')
        
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a
    except Exception: return None, None, None

df_base, df_just, df_agenda = carregar_dados()

if df_base is None:
    st.error("🚨 Erro ao carregar dados.")
    st.stop()

# --- INTERFACE ---
st.sidebar.image("https://marata.com.br/wp-content/uploads/2021/05/logo-marata.png", width=120)
menu = st.sidebar.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    col_sup = 'Região de vendas'
    supervisores = sorted([s for s in df_base[col_sup].unique() if str(s).strip() and str(s) != 'nan'])
    sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)
    
    if sup_sel != "Selecione...":
        clientes_f = df_base[df_base[col_sup] == sup_sel]
        lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
        cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)
        
        if cliente_sel != "Selecione...":
            with st.form("form_novo"):
                data_v = st.date_input("Data da Visita:", datetime.now(fuso_br))
                if st.form_submit_button("💾 CONFIRMAR"):
                    cod_c, nom_c = cliente_sel.split(" - ", 1)
                    agora_br = datetime.now(fuso_br)
                    agora_str = agora_br.strftime("%d/%m/%Y %H:%M") 
                    novo_id = agora_br.strftime("%Y%m%d%H%M%S")
                    
                    nova_linha = pd.DataFrame([{
                        "ID": novo_id, "REGISTRO": agora_str, "DATA": data_v.strftime("%d/%m/%Y"), 
                        "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, 
                        "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)"
                    }])
                    
                    df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova_linha], ignore_index=True)
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                    st.cache_data.clear()
                    st.success(f"✅ Agendado!")
                    st.rerun()

elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    if not df_agenda.empty:
        # Filtro simples
        f_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + sorted(df_agenda['SUPERVISOR'].unique()))
        df_f = df_agenda.copy()
        if f_sup != "Todos":
            df_f = df_f[df_f['SUPERVISOR'] == f_sup]
        
        # Exibição
        cols_v = ['LINHA', 'REGISTRO', 'DATA', 'SUPERVISOR', 'CÓDIGO CLIENTE', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        df_exibir = df_f[cols_v]

        c1, c2, _ = st.columns([1, 1, 2])
        with c1: st.download_button("📥 Excel", data=converter_para_excel(df_exibir), file_name="agenda_marata.xlsx")
        with c2: st.download_button("📄 PDF", data=gerar_pdf(df_exibir), file_name="agenda_marata.pdf")

        # Tabela interativa (usuário clica na coluna para ordenar)
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📝 Editar ou Excluir")
        dict_l = {f"Linha {row['LINHA']} | {row['DATA']} - {row['CLIENTE']}": row['ID'] for idx, row in df_f.iterrows()}
        edit_sel = st.selectbox("Selecione a visita:", ["Selecione..."] + list(dict_l.keys()))
        
        if edit_sel != "Selecione...":
            id_s = dict_l[edit_sel]
            match = df_agenda[df_agenda['ID'] == id_s]
            if not match.empty:
                dv = match.iloc[0]
                with st.form("form_edit"):
                    st_list = ["Planejado (X)", "Realizado", "Reagendado"]
                    ju_list = list(df_just.iloc[:, 0].dropna().unique())
                    n_st = st.radio("Status:", st_list, index=st_list.index(dv['STATUS']) if dv['STATUS'] in st_list else 0, horizontal=True)
                    n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(dv['JUSTIFICATIVA']) if dv['JUSTIFICATIVA'] in ju_list else 0)
                    
                    c_b1, c_b2 = st.columns(2)
                    with c_b1:
                        if st.form_submit_button("✅ ATUALIZAR"):
                            df_save = df_agenda.drop(columns=['LINHA'], errors='ignore')
                            df_save.loc[df_save['ID'] == id_s, 'STATUS'] = n_st
                            df_save.loc[df_save['ID'] == id_s, 'JUSTIFICATIVA'] = n_ju
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save)
                            st.cache_data.clear()
                            st.rerun()
                    with c_b2:
                        if st.form_submit_button("🗑️ EXCLUIR"):
                            df_save = df_agenda[df_agenda['ID'] != id_s].drop(columns=['LINHA'], errors='ignore')
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save)
                            st.cache_data.clear()
                            st.rerun()
    else:
        st.info("Agenda vazia.")
