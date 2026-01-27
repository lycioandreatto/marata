import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
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
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        # Limpa cabeçalhos
        for df in [df_b, df_j, df_a, df_u]:
            if df is not None:
                df.columns = [str(c).strip().upper() for c in df.columns]
        
        return df_b, df_j, df_a, df_u
    except:
        return None, None, None, None

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- TELA DE LOGIN (REFORMULADA) ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.title("☕ MARATÁ")
        st.subheader("Acesso ao Sistema")
        u_input = st.text_input("Usuário").strip()
        s_input = st.text_input("Senha", type="password").strip()
        
        if st.button("ENTRAR", use_container_width=True):
            if df_usuarios is not None:
                # Compara ignorando maiúsculas e espaços
                usuarios_lista = df_usuarios['USUARIO'].str.strip().str.lower()
                senhas_lista = df_usuarios['SENHA'].astype(str).str.strip().str.lower()
                
                if u_input.lower() in usuarios_lista.values:
                    idx = usuarios_lista[usuarios_lista == u_input.lower()].index[0]
                    if s_input.lower() == senhas_lista[idx]:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = df_usuarios.iloc[idx]['USUARIO']
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")
            else:
                st.error("Erro ao carregar banco de usuários.")
    st.stop()

# --- LOGICA DE ADMIN ---
eh_admin = st.session_state.usuario_nome.lower() == "lycio"

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("Menu")
    st.write(f"Conectado: **{st.session_state.usuario_nome}**")
    menu = st.selectbox("Escolha uma opção:", ["Novo Agendamento", "Minha Agenda"])
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# 1. NOVO AGENDAMENTO
if menu == "Novo Agendamento":
    st.header("📋 Agendar Visita")
    
    if eh_admin:
        sups = sorted([s for s in df_base['REGIÃO DE VENDAS'].unique() if str(s) != 'nan' and str(s) != ''])
        sup_alvo = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
    else:
        sup_alvo = st.session_state.usuario_nome

    if sup_alvo and sup_alvo != "Selecione...":
        clientes_f = df_base[df_base['REGIÃO DE VENDAS'] == sup_alvo].copy()
        
        if not clientes_f.empty:
            # Captura Analista (Coluna A)
            nome_analista = str(clientes_f.iloc[0, 0])
            
            # Limpa os dados dos clientes para não aparecer ".0" ou "nan"
            for col in ['CLIENTE', 'NOME 1']:
                clientes_f[col] = clientes_f[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
            
            lista_clientes = sorted(clientes_f.apply(lambda x: f"{x['CLIENTE']} - {x['NOME 1']}", axis=1).tolist())
            cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_clientes)
            
            if cliente_sel != "Selecione...":
                with st.form("f_salvar"):
                    data_v = st.date_input("Data da Visita:", datetime.now(fuso_br))
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
                        st.success("Gravado com sucesso!")
                        st.rerun()

# 2. MINHA AGENDA
elif menu == "Minha Agenda":
    st.header("🔍 Visualizar Agenda")
    df_f = df_agenda.copy() if df_agenda is not None else pd.DataFrame()
    
    if not eh_admin and not df_f.empty:
        df_f = df_f[df_f['SUPERVISOR'] == st.session_state.usuario_nome]
    elif eh_admin and not df_f.empty:
        f_sup = st.selectbox("Filtrar Visão:", ["Todos"] + sorted(df_f['SUPERVISOR'].unique().tolist()))
        if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]

    if not df_f.empty:
        df_f["EDITAR"] = False
        cols_v = ['EDITAR', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        cols_v = [c for c in cols_v if c in df_f.columns or c == 'EDITAR']
        
        edicao = st.data_editor(df_f[cols_v], column_config={"EDITAR": st.column_config.CheckboxColumn("📝")}, disabled=[c for c in cols_v if c != "EDITAR"], hide_index=True, use_container_width=True)

        marcadas = edicao[edicao["EDITAR"] == True]
        if not marcadas.empty:
            idx = marcadas.index[0]
            linha = df_f.loc[idx]
            
            with st.form("edit_form"):
                st.subheader(f"Editar: {linha['CLIENTE']}")
                st_list = ["Planejado (X)", "Realizado", "Reagendado", "OUTRO"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                n_st = st.selectbox("Status:", st_list, index=st_list.index(linha['STATUS']) if linha['STATUS'] in st_list else 0)
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(linha['JUSTIFICATIVA']) if linha['JUSTIFICATIVA'] in ju_list else 0)
                
                obs = st.text_input("Observação (Caso marcou OUTRO):")

                if st.form_submit_button("✅ SALVAR"):
                    v_st = obs if n_st == "OUTRO" and obs else n_st
                    v_ju = obs if n_ju == "OUTRO" and obs else n_ju
                    
                    df_agenda.loc[df_agenda['ID'] == str(linha['ID']), ['STATUS', 'JUSTIFICATIVA']] = [v_st, v_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
