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

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=10) # Cache curto para refletir mudanças rápido
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

# --- INTERFACE ---
st.sidebar.image("https://marata.com.br/wp-content/uploads/2021/05/logo-marata.png", width=120)
menu = st.sidebar.selectbox("Menu", ["Novo Agendamento", "Ver/Editar Minha Agenda"])

if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
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
                    st.rerun()

elif menu == "Ver/Editar Minha Agenda":
    st.header("🔍 Minha Agenda")
    
    # Criamos uma coluna de estado para saber qual ID está sendo editado
    if "id_para_editar" not in st.session_state:
        st.session_state.id_para_editar = None

    f_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + sorted(df_agenda['SUPERVISOR'].unique()))
    df_f = df_agenda.copy()
    if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]

    # Adicionamos a coluna de "BOTÃO" fictícia para o editor
    df_f["EDITAR"] = False 

    cols_v = ['EDITAR', 'REGISTRO', 'DATA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
    
    # O Data Editor permite o clique
    edicao = st.data_editor(
        df_f[cols_v],
        column_config={
            "EDITAR": st.column_config.CheckboxColumn(
                "📝",
                help="Marque para editar esta linha",
                default=False,
            ),
        },
        disabled=[c for c in cols_v if c != "EDITAR"],
        hide_index=True,
        use_container_width=True,
        key="tabela_editor"
    )

    # Verifica se alguma linha foi marcada no Checkbox
    linhas_marcadas = edicao[edicao["EDITAR"] == True]
    
    if not linhas_marcadas.empty:
        # Pegamos o índice da primeira linha marcada
        idx_original = linhas_marcadas.index[0]
        dados_linha = df_f.loc[idx_original]
        id_s = dados_linha['ID']
        
        st.markdown(f"---")
        st.subheader(f"⚙️ Opções para: {dados_linha['CLIENTE']}")
        
        with st.form("form_edit_final"):
            c1, c2 = st.columns(2)
            st_list = ["Planejado (X)", "Realizado", "Reagendado"]
            ju_list = list(df_just.iloc[:, 0].dropna().unique())
            
            with c1:
                n_st = st.radio("Status:", st_list, index=st_list.index(dados_linha['STATUS']) if dados_linha['STATUS'] in st_list else 0)
            with c2:
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(dados_linha['JUSTIFICATIVA']) if dados_linha['JUSTIFICATIVA'] in ju_list else 0)
            
            b_at, b_ex = st.columns(2)
            with b_at:
                if st.form_submit_button("✅ SALVAR ALTERAÇÕES", use_container_width=True):
                    df_agenda.loc[df_agenda['ID'] == id_s, ['STATUS', 'JUSTIFICATIVA']] = [n_st, n_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA']))
                    st.cache_data.clear()
                    st.success("Atualizado!")
                    st.rerun()
            with b_ex:
                if st.form_submit_button("🗑️ EXCLUIR DEFINITIVAMENTE", use_container_width=True):
                    df_novo = df_agenda[df_agenda['ID'] != id_s].drop(columns=['LINHA'])
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_novo)
                    st.cache_data.clear()
                    st.warning("Excluído!")
                    st.rerun()
