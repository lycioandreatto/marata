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
@st.cache_data(ttl=10)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        
        df_a.columns = [str(c).strip() for c in df_a.columns]
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
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

# --- BARRA LATERAL ---
with st.sidebar:
    # Ajustado para o novo nome do arquivo
    try:
        st.image("pngmarata.png", use_container_width=True)
    except:
        # Tenta sem a extensão caso você tenha nomeado apenas como pngmarata no GitHub
        try:
            st.image("pngmarata", use_container_width=True)
        except:
            st.warning("Arquivo 'pngmarata.png' não encontrado no GitHub.")
    
    st.markdown("### 📋 Painel de Controle")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

    st.markdown("---")
    st.subheader("🗑️ Limpeza em Massa")
    if df_agenda is not None and not df_agenda.empty:
        lista_supervisores = sorted(df_agenda['SUPERVISOR'].unique())
        sup_para_limpar = st.sidebar.selectbox("Limpar toda agenda de:", ["Selecione..."] + lista_supervisores)
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
        supervisores = sorted([s for s in df_base['Região de vendas'].unique() if str(s).strip() and str(s) != 'nan'])
        sup_sel = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + supervisores)
        if sup_sel != "Selecione...":
            clientes_f = df_base[df_base['Região de vendas'] == sup_sel]
            lista_c = sorted(clientes_f.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)
            if cliente_sel != "Selecione...":
                with st.form("form_novo"):
                    data_v = st.date_input("Data da Visita:", datetime.now(fuso_br))
                    if st.form_submit_button("💾 CONFIRMAR"):
                        cod_c, nom_c = cliente_sel.split(" - ", 1)
                        agora_str = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                        novo_id = datetime.now(fuso_br).strftime("%Y%m%d%H%M%S")
                        nova_linha = pd.DataFrame([{"ID": novo_id, "REGISTRO": agora_str, "DATA": data_v.strftime("%d/%m/%Y"), "SUPERVISOR": sup_sel, "CÓDIGO CLIENTE": cod_c, "CLIENTE": nom_c, "JUSTIFICATIVA": "-", "STATUS": "Planejado (X)"}])
                        df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                        st.cache_data.clear()
                        st.success("✅ Agendado!")
                        st.rerun()

# --- PÁGINA: VER/EDITAR ---
elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    if df_agenda is not None and not df_agenda.empty:
        f_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + sorted(df_agenda['SUPERVISOR'].unique()))
        df_f = df_agenda.copy()
        if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]

        # Exportação
        df_exportar = df_f[['REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']]
        c_exp1, c_exp2, _ = st.columns([1, 1, 2])
        with c_exp1:
            st.download_button("📥 Excel", data=converter_para_excel(df_exportar), file_name="agenda_marata.xlsx", use_container_width=True)
        with c_exp2:
            try:
                st.download_button("📄 PDF", data=gerar_pdf(df_exportar), file_name="agenda_marata.pdf", use_container_width=True)
            except:
                st.error("Erro no PDF")

        # Tabela de Edição
        df_f["EDITAR"] = False 
        cols_v = ['EDITAR', 'REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        edicao = st.data_editor(
            df_f[cols_v],
            column_config={"EDITAR": st.column_config.CheckboxColumn("📝", default=False)},
            disabled=[c for c in cols_v if c != "EDITAR"],
            hide_index=True,
            use_container_width=True,
            key="editor_v5"
        )

        linhas_marcadas = edicao[edicao["EDITAR"] == True]
        if not linhas_marcadas.empty:
            idx = linhas_marcadas.index[0]
            dados = df_f.loc[idx]
            id_s = dados['ID']
            st.markdown(f"---")
            st.subheader(f"⚙️ Opções para: {dados['CLIENTE']}")
            with st.form("form_edit_v5"):
                c1, c2 = st.columns(2)
                st_list = ["Planejado (X)", "Realizado", "Reagendado"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                with c1: n_st = st.radio("Status:", st_list, index=st_list.index(dados['STATUS']) if dados['STATUS'] in st_list else 0)
                with c2: n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(dados['JUSTIFICATIVA']) if dados['JUSTIFICATIVA'] in ju_list else 0)
                b_at, b_ex = st.columns(2)
                with b_at:
                    if st.form_submit_button("✅ SALVAR", use_container_width=True):
                        df_agenda.loc[df_agenda['ID'] == id_s, ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                        st.cache_data.clear()
                        st.rerun()
                with b_ex:
                    if st.form_submit_button("🗑️ EXCLUIR", use_container_width=True):
                        df_novo = df_agenda[df_agenda['ID'] != id_s].drop(columns=['LINHA'], errors='ignore')
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_novo)
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("Agenda vazia.")
