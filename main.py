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
@st.cache_data(ttl=2)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        # Padronização segura
        for df in [df_b, df_j, df_a, df_u]:
            if df is not None:
                # 1. Limpa nomes das colunas (Tudo para MAIÚSCULO e sem espaços)
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                # 2. Limpa os dados de cada coluna individualmente para evitar o erro 'str'
                for col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '').str.strip()
        
        return df_b, df_j, df_a, df_u
    except Exception as e:
        st.error(f"Erro crítico no carregamento: {e}")
        return None, None, None, None

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- LOGIN ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.title("☕ MARATÁ")
        u_in = st.text_input("Usuário").strip()
        s_in = st.text_input("Senha", type="password").strip()
        if st.button("ACESSAR", use_container_width=True):
            if df_usuarios is not None:
                # Busca segura
                u_col = df_usuarios['USUARIO'].str.lower()
                if u_in.lower() in u_col.values:
                    idx = u_col[u_col == u_in.lower()].index[0]
                    if str(df_usuarios.iloc[idx]['SENHA']) == s_in:
                        st.session_state.autenticado = True
                        st.session_state.usuario_nome = df_usuarios.iloc[idx]['USUARIO']
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("Usuário não encontrado.")
    st.stop()

eh_admin = st.session_state.usuario_nome.lower() == "lycio"

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"Usuário: **{st.session_state.usuario_nome}**")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Minha Agenda"])
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

# 1. NOVO AGENDAMENTO
if menu == "Novo Agendamento":
    st.header("📋 Registrar Agendamento")
    
    # "Região de vendas" agora é "REGIÃO DE VENDAS" por causa da padronização
    if eh_admin:
        sups = sorted([s for s in df_base['REGIÃO DE VENDAS'].unique() if s != ''])
        sup_alvo = st.selectbox("Selecione o Supervisor:", ["Selecione..."] + sups)
    else:
        sup_alvo = st.session_state.usuario_nome

    if sup_alvo != "Selecione...":
        clientes_f = df_base[df_base['REGIÃO DE VENDAS'] == sup_alvo]
        
        if not clientes_f.empty:
            # Puxa o analista da Coluna A (BASE)
            nome_analista = clientes_f.iloc[0]['ANALISTA']
            
            # Monta lista (Nomes de colunas agora em MAIÚSCULO)
            lista_cli = sorted(clientes_f.apply(lambda x: f"{x['CLIENTE']} - {x['NOME 1']}", axis=1).tolist())
            cliente_sel = st.selectbox("Cliente:", ["Selecione..."] + lista_cli)
            
            if cliente_sel != "Selecione...":
                with st.form("f_add"):
                    data_v = st.date_input("Data:", datetime.now(fuso_br))
                    if st.form_submit_button("SALVAR"):
                        cod_c, nom_c = cliente_sel.split(" - ", 1)
                        agora = datetime.now(fuso_br)
                        novo_id = agora.strftime("%Y%m%d%H%M%S")
                        
                        nova_linha = pd.DataFrame([{
                            "ID": novo_id,
                            "DATA": data_v.strftime("%d/%m/%Y"),
                            "SUPERVISOR": sup_alvo,
                            "CÓDIGO CLIENTE": cod_c,
                            "CLIENTE": nom_c,
                            "JUSTIFICATIVA": "-",
                            "STATUS": "Planejado (X)",
                            "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"),
                            "ANALISTA": nome_analista
                        }])
                        
                        df_final = pd.concat([df_agenda, nova_linha], ignore_index=True)
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final)
                        st.cache_data.clear()
                        st.success(f"Gravado! Analista: {nome_analista}")
                        st.rerun()

# 2. MINHA AGENDA
elif menu == "Minha Agenda":
    st.header("🔍 Gerenciar Agenda")
    df_f = df_agenda.copy()
    
    if not eh_admin:
        df_f = df_f[df_f['SUPERVISOR'] == st.session_state.usuario_nome]
    else:
        f_sup = st.selectbox("Filtrar:", ["Todos"] + sorted(df_f['SUPERVISOR'].unique().tolist()))
        if f_sup != "Todos": df_f = df_f[df_f['SUPERVISOR'] == f_sup]

    if not df_f.empty:
        df_f["EDITAR"] = False
        cols_v = ['EDITAR', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'STATUS', 'JUSTIFICATIVA']
        edicao = st.data_editor(df_f[cols_v], 
                                column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                                disabled=[c for c in cols_v if c != "EDITAR"],
                                hide_index=True, use_container_width=True)

        check = edicao[edicao["EDITAR"] == True]
        if not check.empty:
            idx = check.index[0]
            id_sel = df_f.loc[idx, 'ID']
            
            with st.form("f_edit"):
                st.write(f"Editando: {df_f.loc[idx, 'CLIENTE']}")
                st_list = ["Planejado (X)", "Realizado", "Reagendado", "OUTRO"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                n_st = st.selectbox("Status:", st_list, index=st_list.index(df_f.loc[idx, 'STATUS']) if df_f.loc[idx, 'STATUS'] in st_list else 0)
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(df_f.loc[idx, 'JUSTIFICATIVA']) if df_f.loc[idx, 'JUSTIFICATIVA'] in ju_list else 0)
                obs = st.text_input("Obs (Caso marcou OUTRO):")

                if st.form_submit_button("CONFIRMAR"):
                    v_st = obs if n_st == "OUTRO" and obs else n_st
                    v_ju = obs if n_ju == "OUTRO" and obs else n_ju
                    
                    df_agenda.loc[df_agenda['ID'] == id_sel, ['STATUS', 'JUSTIFICATIVA']] = [v_st, v_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                    st.cache_data.clear()
                    st.rerun()
