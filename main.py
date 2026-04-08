import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ===== 1. CONFIGURAÇÃO DA PÁGINA =====
st.set_page_config(page_title="Brava Brasa", page_icon="🔥", layout="wide")

# ===== 2. CONEXÃO FIREBASE =====
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro de conexão Firebase: {e}")

db = firestore.client()

# ===== 3. ESTRUTURA DO CARDÁPIO =====
CARDAPIO_ESTRUTURA = {
    "🍢 ESPETINHOS": [
        "CARNE", "FRANGO", "CALABRESA", "MISTO", "CORAÇÃO", "QUEIJO"
    ],
    "🥤 BEBIDAS": [
        "COCA LATA", "FANTA LATA", "GUARANÁ LATA", "ÁGUA MINERAL", 
        "ITAIPAVA", "AMSTEL", "HEINEKEN", "ICE CABARÉ", 
        "VINHO - TAÇA", "DOSE PITÚ", "DREHER"
    ]
}

def carregar_precos():
    precos_ref = db.collection("precos").stream()
    carregados = {doc.id: doc.to_dict().get("valor", 0.0) for doc in precos_ref}
    
    padrao = {
        "CARNE": 8.0, "FRANGO": 7.0, "CALABRESA": 7.0, "MISTO": 9.0, "CORAÇÃO": 8.0, "QUEIJO": 7.0,
        "COCA LATA": 6.0, "FANTA LATA": 6.0, "GUARANÁ LATA": 6.0, "ÁGUA MINERAL": 4.0,
        "ITAIPAVA": 8.0, "AMSTEL": 9.0, "HEINEKEN": 12.0, "ICE CABARÉ": 10.0,
        "VINHO - TAÇA": 12.0, "DOSE PITÚ": 5.0, "DREHER": 6.0
    }
    
    for item, valor in padrao.items():
        if item not in carregados:
            carregados[item] = valor
            db.collection("precos").document(item).set({"valor": valor})
    return carregados

def salvar_rascunho_firebase(mesa, itens):
    itens_filtrados = {k: v for k, v in itens.items() if v > 0}
    if itens_filtrados:
        db.collection("pedidos_pendentes").document(mesa).set({"itens": itens_filtrados})
    else:
        db.collection("pedidos_pendentes").document(mesa).delete()

def carregar_rascunhos_firebase():
    docs = db.collection("pedidos_pendentes").stream()
    return {doc.id: doc.to_dict().get("itens", {}) for doc in docs}

# ===== 4. INICIALIZAÇÃO E ESTADO =====
BRASIL = pytz.timezone("America/Sao_Paulo")
precos = carregar_precos()

if "pedidos_ativos" not in st.session_state:
    rascunhos = carregar_rascunhos_firebase()
    mesas_ordenadas = {}
    for i in range(1, 13):
        nome_mesa = f"Mesa {i}"
        base = {item: 0 for cat in CARDAPIO_ESTRUTURA.values() for item in cat}
        if nome_mesa in rascunhos:
            base.update(rascunhos[nome_mesa])
        mesas_ordenadas[nome_mesa] = base
    st.session_state.pedidos_ativos = mesas_ordenadas

if "pagina" not in st.session_state: st.session_state.pagina = "mesas"
if "mesa_atual" not in st.session_state: st.session_state.mesa_atual = None

# ===== 5. ESTILO CSS (MOBILE FIX & COMANDA) =====
st.markdown("""
<style>
    /* Forçar 2 colunas reais no mobile */
    [data-testid="column"] {
        width: 50% !important;
        flex: 1 1 50% !important;
        min-width: 45% !important;
    }
    [data-testid="stHorizontalBlock"] {
        display: flex;
        flex-wrap: wrap;
        flex-direction: row !important;
    }
    /* Estilo dos Botões e Cards */
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; margin-bottom: 5px; }
    .card-mesa { padding: 10px; border-radius: 12px; text-align: center; margin-top: 10px; font-size: 1.1em; }
    .total-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: #ff6600; color: white; 
                 text-align: center; padding: 15px; font-size: 22px; font-weight: bold; z-index: 999; border-top: 2px solid white; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# ===== 6. NAVEGAÇÃO =====
with st.sidebar:
    st.title("🔥 Brava Brasa")
    menu = st.radio("Menu", ["Mesas / Pedidos", "Relatório Detalhado", "Ajustar Preços"])

if menu == "Relatório Detalhado": st.session_state.pagina = "relatorio"
elif menu == "Ajustar Preços": st.session_state.pagina = "precos"
else: 
    if st.session_state.pagina not in ["pedido"]: st.session_state.pagina = "mesas"

# =========================
# PÁGINA: MESAS
# =========================
if st.session_state.pagina == "mesas":
    st.header("🍽️ Mesas Ativas")
    lista_mesas = [f"Mesa {i}" for i in range(1, 13)]
    
    for i in range(0, len(lista_mesas), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(lista_mesas):
                nome = lista_mesas[i + j]
                with cols[j]:
                    itens_mesa = st.session_state.pedidos_ativos.get(nome, {})
                    ocupada = any(v > 0 for v in itens_mesa.values())
                    cor = "#ff4b4b" if ocupada else "#28a745"
                    st.markdown(f'<div class="card-mesa" style="border: 2px solid {cor};"><b>{nome}</b></div>', unsafe_allow_html=True)
                    if st.button(f"Abrir", key=f"btn_{nome}"):
                        st.session_state.mesa_atual = nome
                        st.session_state.pagina = "pedido"
                        st.rerun()

# =========================
# PÁGINA: PEDIDO (CARDÁPIO)
# =========================
elif st.session_state.pagina == "pedido":
    mesa = st.session_state.mesa_atual
    itens_atuais = st.session_state.pedidos_ativos[mesa]
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⬅️ Voltar"):
            st.session_state.pagina = "mesas"
            st.rerun()
    with c2:
        st.write(f"### {mesa}")

    # --- NOVO: RESUMO DA COMANDA ---
    pedidos_ativos = {item: qtd for item, qtd in itens_atuais.items() if qtd > 0}
    if pedidos_ativos:
        with st.expander("📝 Comanda Atual", expanded=True):
            subtotal_comanda = 0
            for item, qtd in pedidos_ativos.items():
                v_unit = precos.get(item, 0.0)
                sub = v_unit * qtd
                subtotal_comanda += sub
                st.markdown(f"**{qtd}x** {item} <span style='float:right;'>R$ {sub:.2f}</span>", unsafe_allow_html=True)
            st.divider()
            st.markdown(f"**Total Parcial: <span style='float:right;'>R$ {subtotal_comanda:.2f}</span>**", unsafe_allow_html=True)

    tab_esp, tab_beb = st.tabs(["🍢 ESPETINHOS", "🥤 BEBIDAS"])

    def render_categoria(lista_itens):
        for item in lista_itens:
            valor = precos.get(item, 0.0)
            qtd = st.session_state.pedidos_ativos[mesa].get(item, 0)
            
            col_txt, col_men, col_num, col_mai = st.columns([2, 1, 1, 1])
            with col_txt: 
                st.markdown(f"**{item}**\nR$ {valor:.2f}")
            with col_men:
                if st.button("➖", key=f"sub_{item}_{mesa}"):
                    if st.session_state.pedidos_ativos[mesa][item] > 0:
                        st.session_state.pedidos_ativos[mesa][item] -= 1
                        salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                        st.rerun()
            with col_num: 
                st.markdown(f"<h3 style='text-align:center;'>{qtd}</h3>", unsafe_allow_html=True)
            with col_mai:
                if st.button("➕", key=f"add_{item}_{mesa}"):
                    st.session_state.pedidos_ativos[mesa][item] += 1
                    salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                    st.rerun()
            st.divider()

    with tab_esp: render_categoria(CARDAPIO_ESTRUTURA["🍢 ESPETINHOS"])
    with tab_beb: render_categoria(CARDAPIO_ESTRUTURA["🥤 BEBIDAS"])

    total = sum(st.session_state.pedidos_ativos[mesa][i] * precos.get(i, 0) for i in st.session_state.pedidos_ativos[mesa])
    st.markdown(f"<div class='total-bar'>TOTAL: R$ {total:.2f}</div>", unsafe_allow_html=True)
    st.write("\n\n\n")

    if total > 0:
        if st.button("✅ FINALIZAR CONTA", use_container_width=True):
            agora = datetime.now(BRASIL)
            pedido_final = {
                "mesa": mesa,
                "itens": {k: v for k, v in st.session_state.pedidos_ativos[mesa].items() if v > 0},
                "total": total,
                "data": agora.strftime("%Y-%m-%d"),
                "hora": agora.strftime("%H:%M")
            }
            db.collection("pedidos").add(pedido_final)
            db.collection("pedidos_pendentes").document(mesa).delete()
            st.session_state.pedidos_ativos[mesa] = {item: 0 for cat in CARDAPIO_ESTRUTURA.values() for item in cat}
            st.success("Pedido Salvo!")
            st.session_state.pagina = "mesas"
            st.rerun()

# =========================
# PÁGINA: RELATÓRIO
# =========================
elif st.session_state.pagina == "relatorio":
    st.header("📊 Vendas")
    data_sel = st.date_input("Data", datetime.now(BRASIL))
    data_str = data_sel.strftime("%Y-%m-%d")
    docs = db.collection("pedidos").where("data", "==", data_str).stream()
    vendas = sorted([d.to_dict() for d in docs], key=lambda x: x['hora'], reverse=True)
    if vendas:
        st.metric("Total Vendido", f"R$ {sum(v['total'] for v in vendas):.2f}")
        for v in vendas:
            with st.expander(f"{v['hora']} - {v['mesa']} | R$ {v['total']:.2f}"):
                for item, qtd in v['itens'].items(): st.write(f"{qtd}x {item}")
    else: st.info("Sem vendas.")

# =========================
# PÁGINA: AJUSTAR PREÇOS
# =========================
elif st.session_state.pagina == "precos":
    st.header("⚙️ Preços")
    for cat, itens in CARDAPIO_ESTRUTURA.items():
        st.subheader(cat)
        for item in itens:
            v_atual = float(precos.get(item, 0.0))
            novo_v = st.number_input(f"{item}", value=v_atual, step=0.5, key=f"p_{item}")
            if novo_v != v_atual:
                db.collection("precos").document(item).set({"valor": novo_v})
                st.toast(f"{item} atualizado!")
