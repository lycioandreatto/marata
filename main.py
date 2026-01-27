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

# --- CARREGAMENTO E LIMPEZA TOTAL ---
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        # 1. Normaliza cabeçalhos (Maiúsculas e sem espaços)
        for df in [df_b, df_j, df_a, df_u]:
            if df is not None:
                df.columns = [str(c).strip().upper() for c in df.columns]
                # 2. Limpeza profunda de cada célula: converte tudo para string limpa
                for col in df.columns:
                    df[col] = df[col].astype(str).str.strip().replace(r'\.0$', '', regex=True).replace('nan', '')
        
        return df_b, df_j, df_a, df_u
    except:
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
                match = df_usuarios[(df_usuarios['USUARIO'].str.lower() == u.lower()) & (df_usuarios['SENHA'] == s)]
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario_nome = match.iloc[0]['USUARIO']
                    st.rerun()
    st.stop()

eh_admin = st.session_state.usuario_nome.lower() == "lycio"

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("☕ Gestão Maratá")
    st.write(f"Usuário: **{st.session_state.usuario_nome}**")
    menu = st.selectbox("Menu", ["Novo Agendamento", "Minha Agenda"])
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# 1. NOVO AGENDAMENTO
if menu == "Novo Agendamento":
    st.header("📋 Novo Agendamento")
    
    if eh_admin:
        sups = sorted([s for s in df_base['REGIÃO DE VENDAS'].unique() if s != ''])
        sup_alvo = st.selectbox("Escolha o Supervisor:", ["Selecione..."] + sups)
    else:
        sup_alvo = st.session_state.usuario_nome

    if sup_alvo != "Selecione...":
        clientes_f = df_base[df_base['REGIÃO DE VENDAS'] == sup_alvo]
        
        if clientes_f.empty:
            st.warning(f"Sem clientes para {sup_alvo}")
        else:
            # Captura Analista (Coluna A)
            nome_analista = str(clientes_f.iloc[0, 0])
            
            # Montagem da lista sem "sujeira" técnica
            lista_clientes = []
            for _, row in clientes_f.iterrows():
                # Forçamos o valor puro da string
                cod = str(row['CLIENTE']).strip()
                nome = str(row['NOME 1']).strip()
                lista_clientes.append(f"{cod} - {nome}")
            
            cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + sorted(lista_clientes))
            
            if cliente_sel != "Selecione...":
                with st.form("save_form"):
                    data_v = st.date_input("Data da Visita:", datetime.now(fuso_br))
                    if st.form_submit_button("💾 SALVAR NA AGENDA"):
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
                        st.success(f"Agendado! Analista: {nome_analista}")
                        st.rerun()

# 2. VISUALIZAR AGENDA
elif menu == "Minha Agenda":
    st.header("🔍 Visualizar Agenda")
    df_exibir = df_agenda.copy()
    
    if not eh_admin:
        df_exibir = df_exibir[df_exibir['SUPERVISOR'] == st.session_state.usuario_nome]
    else:
        f_sup = st.selectbox("Filtrar por Supervisor:", ["Todos"] + sorted(df_agenda['SUPERVISOR'].unique().tolist()))
        if f_sup != "Todos":
            df_exibir = df_exibir[df_exibir['SUPERVISOR'] == f_sup]

    if not df_exibir.empty:
        df_exibir["EDITAR"] = False
        colunas = ['EDITAR', 'DATA', 'ANALISTA', 'SUPERVISOR', 'CLIENTE', 'JUSTIFICATIVA', 'STATUS']
        # Filtra apenas colunas que realmente existem para não dar erro
        colunas_existem = [c for c in colunas if c in df_exibir.columns]
        
        edicao = st.data_editor(df_exibir[colunas_existem], 
                                column_config={"EDITAR": st.column_config.CheckboxColumn("📝")},
                                disabled=[c for c in colunas_existem if c != "EDITAR"],
                                hide_index=True, use_container_width=True)

        # Lógica de Edição para "OUTRO"
        selecionado = edicao[edicao["EDITAR"] == True]
        if not selecionado.empty:
            idx = selecionado.index[0]
            linha_orig = df_exibir.loc[idx]
            
            with st.form("edit_area"):
                st.write(f"Editando: {linha_orig['CLIENTE']}")
                st_list = ["Planejado (X)", "Realizado", "Reagendado", "OUTRO"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                n_st = st.selectbox("Status:", st_list, index=st_list.index(linha_orig['STATUS']) if linha_orig['STATUS'] in st_list else 0)
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(linha_orig['JUSTIFICATIVA']) if linha_orig['JUSTIFICATIVA'] in ju_list else 0)
                
                obs = st.text_input("Se escolheu 'OUTRO', digite aqui:")

                if st.form_submit_button("✅ SALVAR"):
                    # Se digitou algo na observação, usa ela
                    f_st = obs if n_st == "OUTRO" and obs else n_st
                    f_ju = obs if n_ju == "OUTRO" and obs else n_ju
                    
                    df_agenda.loc[df_agenda['ID'] == linha_orig['ID'], ['STATUS', 'JUSTIFICATIVA']] = [f_st, f_ju]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
