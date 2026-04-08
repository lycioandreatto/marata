import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import re

# ===== CONFIGURAÇÃO DA PÁGINA =====
st.set_page_config(page_title="Brava Brasa", page_icon="🔥", layout="wide")

# ===== CONEXÃO FIREBASE =====
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro de conexão Firebase: {e}")

db = firestore.client()

# ===== ESTRUTURA DO CARDÁPIO =====
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

# ===== INICIALIZAÇÃO E ORDENAÇÃO =====
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

# ===== ESTILO CSS (TRAVA LAYOUT MOBILE COMPACTO) =====
st.markdown("""
<style>
    /* Forçar colunas a ficarem lado a lado (Row) em vez de empilhar */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }
    
    [data-testid="column"] {
        min-width: 0px !important;
        flex: 1 1 auto !important;
    }

    /* Botões de +/- menores */
    [data-testid="column"] button {
        height: 2.5em !important;
        padding: 0px !important;
        min-width: 40px !important;
    }
    
    /* Botões Grandes (Mesa e Finalizar) permanecem normais */
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    
    .card-mesa { padding: 10px; border-radius: 12px; text-align: center; margin-bottom: 5px; }
    
    .total-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: #ff6600; color: white; 
                 text-align: center; padding: 15px; font-size: 22px; font-weight: bold; z-index: 999; border-top: 2px solid white; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px; }
    
    /* Ajuste fino para o texto do item não quebrar linha */
    .item-text { font-size: 14px; white-space: nowrap; }
</style>
""", unsafe_allow_html=True)

# ===== NAVEGAÇÃO =====
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
    
    cols = st.columns(2)
    for i, nome in enumerate(lista_mesas):
        with cols[i % 2]:
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
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⬅️ Voltar"):
            st.session_state.pagina = "mesas"
            st.rerun()
    with c2:
        st.write(f"### {mesa}")

    tab_esp, tab_beb = st.tabs(["🍢 ESPETINHOS", "🥤 BEBIDAS"])

    def render_categoria(lista_itens):
        for item in lista_itens:
            valor = precos.get(item, 0.0)
            qtd = st.session_state.pedidos_ativos[mesa].get(item, 0)
            
            # Layout Horizontal Travado: Item(3) | -(1) | Qtd(1) | +(1)
            col_txt, col_men, col_num, col_mai = st.columns([3.5, 1.2, 1, 1.2])
            with col_txt: 
                st.markdown(f"<div class='item-text'><b>{item}</b><br>R$ {valor:.2f}</div>", unsafe_allow_html=True)
            with col_men:
                if st.button("➖", key=f"sub_{item}_{mesa}"):
                    if st.session_state.pedidos_ativos[mesa][item] > 0:
                        st.session_state.pedidos_ativos[mesa][item] -= 1
                        salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                        st.rerun()
            with col_num: 
                st.markdown(f"<h3 style='text-align:center; margin:0;'>{qtd}</h3>", unsafe_allow_html=True)
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
