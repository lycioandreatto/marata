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

# --- ESTADO DE SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_nome' not in st.session_state:
    st.session_state.usuario_nome = ""

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=2) # Diminuído o tempo para ler mudanças na planilha mais rápido
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        # LIMPEZA DE COLUNAS (Remove espaços e garante maiúsculas)
        for df in [df_b, df_j, df_a, df_u]:
            df.columns = [str(c).strip().upper() for c in df.columns]
        
        if df_a is not None:
            df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return None, None, None, None

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- LOGIN ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.title("☕ MARATÁ")
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar", use_container_width=True):
            if df_usuarios is not None:
                # Login ignorando maiúsculas/minúsculas
                match = df_usuarios[(df_usuarios['USUARIO'].str.lower() == u.lower()) & (df_usuarios['SENHA'].astype(str) == s)]
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario_nome = match.iloc[0]['USUARIO']
                    st.rerun()
    st.stop()

eh_admin = st.session_state.usuario_nome.lower() == "lycio"

# --- BARRA LATERAL ---
with st.sidebar:
    st.subheader("☕ Gestão Maratá")
    st.write(f"Logado: **{st.session_state.usuario_nome}**")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Minha Agenda"])
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# 1. NOVO AGENDAMENTO
if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    
    # Define quem é o alvo do agendamento
    if eh_admin:
        lista_sups = sorted([s for s in df_base['REGIÃO DE VENDAS'].unique() if str(s) != 'nan'])
        sup_alvo = st.selectbox("Supervisor:", ["Selecione..."] + lista_sups)
    else:
        sup_alvo = st.session_state.usuario_nome

    if sup_alvo and sup_alvo != "Selecione...":
        clientes_f = df_base[df_base['REGIÃO DE VENDAS'] == sup_alvo]
        if not clientes_f.empty:
            # Tenta pegar Analista, se não existir, usa "Não Definido"
            nome_analista = clientes_f.iloc[0].get('ANALISTA', 'NÃO DEFINIDO')
            
            lista_c = sorted(clientes_f.apply(lambda x: f"{x['CLIENTE']} - {x['NOME 1']}", axis=1).tolist())
            cliente_sel = st.selectbox("Cliente:", ["Selecione..."] + lista_c)
            
            if cliente_sel != "Selecione...":
                with st.form("f_novo"):
                    data_v = st.date_input("Data:", datetime.now(fuso_br))
                    if st.form_submit_button("💾 SALVAR"):
                        cod_c, nom_c = cliente_sel.split(" - ", 1)
                        agora = datetime.now(fuso_br)
                        novo_id = agora.strftime("%Y%m%d%H%M%S")
                        
                        nova_linha = pd.DataFrame([{
                            "ID": novo_id,
                            "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"),
                            "DATA": data_v.strftime("%d/%m/%Y"),
                            "ANALISTA": nome_analista,
                            "SUPERVISOR": sup_alvo,
                            "CÓDIGO CLIENTE": cod_c,
                            "CLIENTE": nom_c,
                            "JUSTIFICATIVA": "-",
                            "STATUS": "Planejado (X)"
                        }])
                        df_final = pd.concat([df_agenda.drop(columns=['LINHA'], errors='ignore'), nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                        st.cache_data.clear()
                        st.success("Agendado!")
                        st.rerun()

# 2. MINHA AGENDA
elif menu == "Minha Agenda":
    st.header("🔍 Visualizar Agenda")
    df_f = df_agenda.copy() if df_agenda is not None else pd.DataFrame()
    
    if not eh_admin and not df_f.empty:
        df_f = df_f[df_f['SUPERVISOR'] == st.session_state.usuario_nome]
    elif eh_admin and not df_f.empty:
        f_sup = st.selectbox("Filtrar Supervisor:", ["Todos"] + sorted(df_f['SUPERVISOR'].unique().tolist()))
        if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]

    if not df_f.empty:
        df_f["EDITAR"] = False
        cols_v = ['EDITAR', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        # Remove colunas que possam não existir para evitar novo KeyError
        cols_v = [c for c in cols_v if c in df_f.columns or c == 'EDITAR']
        
        edicao = st.data_editor(df_f[cols_v], column_config={"EDITAR": st.column_config.CheckboxColumn("📝")}, disabled=[c for c in cols_v if c != "EDITAR"], hide_index=True, use_container_width=True)

        marcadas = edicao[edicao["EDITAR"] == True]
        if not marcadas.empty:
            idx = marcadas.index[0]
            linha = df_f.loc[idx]
            
            with st.form("edit_marata"):
                st.subheader(f"Editar: {linha['CLIENTE']}")
                st_list = ["Planejado (X)", "Realizado", "Reagendado", "OUTRO"]
                # Pega justificativas da aba e garante que "OUTRO" esteja lá
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                n_st = st.selectbox("Status:", st_list, index=st_list.index(linha['STATUS']) if linha['STATUS'] in st_list else 0)
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(linha['JUSTIFICATIVA']) if linha['JUSTIFICATIVA'] in ju_list else 0)
                
                obs_extra = st.text_input("Se selecionou 'OUTRO', digite aqui a observação:")

                if st.form_submit_button("✅ ATUALIZAR"):
                    val_status = obs_extra if n_st == "OUTRO" and obs_extra else n_st
                    val_just = obs_extra if n_ju == "OUTRO" and obs_extra else n_ju
                    
                    df_agenda.loc[df_agenda['ID'] == linha['ID'], ['STATUS', 'JUSTIFICATIVA']] = [val_status, val_just]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.success("Atualizado!")
                    st.rerun()
    else:
        st.info("Nenhum dado encontrado na agenda.")
