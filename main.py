import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
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
        
        for df in [df_b, df_j, df_a, df_u]:
            if df is not None:
                df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Limpeza de strings para evitar o erro da imagem 2
        if df_b is not None:
            for col in df_b.columns:
                df_b[col] = df_b[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
        
        return df_b, df_j, df_a, df_u
    except Exception as e:
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
    st.header(f"📋 Agendar Visita")
    
    # Se for ADM, ele escolhe o supervisor. Se não, usa o próprio login.
    if eh_admin:
        sups = sorted([s for s in df_base['REGIÃO DE VENDAS'].unique() if s and s != ''])
        sup_alvo = st.selectbox("Selecione o Supervisor para agendar:", ["Selecione..."] + sups)
    else:
        sup_alvo = st.session_state.usuario_nome

    # Só prossegue se tiver um supervisor selecionado (ou logado)
    if sup_alvo and sup_alvo != "Selecione...":
        clientes_f = df_base[df_base['REGIÃO DE VENDAS'] == sup_alvo].copy()
        
        if clientes_f.empty:
            st.warning(f"Atenção: Não encontramos clientes para o supervisor '{sup_alvo}'.")
        else:
            # Pega o Analista da Coluna A (Índice 0) garantindo que seja STRING pura
            nome_analista = str(clientes_f.iloc[0, 0])
            
            # FORMATO DA LISTA: Garante que pegue apenas o VALOR do texto
            def formatar_linha(row):
                # .values[0] ou a conversão direta evita o erro "dtype: object" da imagem
                cod = str(row['CLIENTE'])
                nome = str(row['NOME 1'])
                return f"{cod} - {nome}"

            lista_c = sorted([formatar_linha(row) for _, row in clientes_f.iterrows()])
            cliente_sel = st.selectbox("Escolha o Cliente:", ["Selecione..."] + lista_c)
            
            if cliente_sel != "Selecione...":
                with st.form("f_novo"):
                    data_v = st.date_input("Data da Visita:", datetime.now(fuso_br))
                    if st.form_submit_button("💾 SALVAR AGENDAMENTO"):
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
                        st.success(f"Agendado com sucesso para {sup_alvo}!")
                        st.rerun()

# 2. MINHA AGENDA
elif menu == "Minha Agenda":
    st.header("🔍 Visualizar Agenda")
    df_f = df_agenda.copy() if df_agenda is not None else pd.DataFrame()
    
    if not eh_admin and not df_f.empty:
        df_f = df_f[df_f['SUPERVISOR'] == st.session_state.usuario_nome]
    elif eh_admin and not df_f.empty:
        f_sup = st.selectbox("Filtrar Visão por Supervisor:", ["Todos"] + sorted(df_f['SUPERVISOR'].unique().tolist()))
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
            
            with st.form("edit_marata"):
                st.subheader(f"Editar: {linha['CLIENTE']}")
                st_list = ["Planejado (X)", "Realizado", "Reagendado", "OUTRO"]
                ju_list = list(df_just.iloc[:, 0].dropna().unique())
                if "OUTRO" not in ju_list: ju_list.append("OUTRO")
                
                n_st = st.selectbox("Status:", st_list, index=st_list.index(linha['STATUS']) if linha['STATUS'] in st_list else 0)
                n_ju = st.selectbox("Justificativa:", ju_list, index=ju_list.index(linha['JUSTIFICATIVA']) if linha['JUSTIFICATIVA'] in ju_list else 0)
                
                obs_extra = st.text_input("Se marcou 'OUTRO', descreva aqui:")

                if st.form_submit_button("✅ SALVAR"):
                    val_status = obs_extra if n_st == "OUTRO" and obs_extra else n_st
                    val_just = obs_extra if n_ju == "OUTRO" and obs_extra else n_ju
                    
                    df_agenda.loc[df_agenda['ID'] == str(linha['ID']), ['STATUS', 'JUSTIFICATIVA']] = [val_status, val_just]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA'], errors='ignore'))
                    st.cache_data.clear()
                    st.rerun()
