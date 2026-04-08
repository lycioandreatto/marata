import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

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
    "🍢 ESPETINHOS": ["CARNE", "FRANGO", "CALABRESA", "MISTO", "CORAÇÃO", "QUEIJO"],
    "🥤 BEBIDAS": ["COCA LATA", "FANTA LATA", "GUARANÁ LATA", "ÁGUA MINERAL", "ITAIPAVA", "AMSTEL", "HEINEKEN", "ICE CABARÉ", "VINHO - TAÇA", "DOSE PITÚ", "DREHER"]
}

def carregar_precos():
    precos_ref = db.collection("precos").stream()
    carregados = {doc.id: doc.to_dict().get("valor", 0.0) for doc in precos_ref}
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

# ===== INICIALIZAÇÃO =====
BRASIL = pytz.timezone("America/Sao_Paulo")
precos = carregar_precos()

if "pedidos_ativos" not in st.session_state:
    rascunhos = carregar_rascunhos_firebase()
    for mesa in rascunhos:
        base = {item: 0 for cat in CARDAPIO_ESTRUTURA.values() for item in cat}
        base.update(rascunhos[mesa])
        rascunhos[mesa] = base
    st.session_state.pedidos_ativos = rascunhos

if "pagina" not in st.session_state: st.session_state.pagina = "mesas"
if "mesa_atual" not in st.session_state: st.session_state.mesa_atual = None

# ===== ESTILO CSS (O SEGREDO DA ORGANIZAÇÃO) =====
st.markdown("""
<style>
    /* Forçar colunas a ficarem lado a lado no celular */
    [data-testid="column"] {
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 0px !important;
    }
    
    /* Diminuir altura dos botões e fontes */
    .stButton>button {
        height: 35px !important;
        padding: 0px !important;
        font-size: 14px !important;
        margin: 0px !important;
    }
    
    /* Estilo do Nome do Item */
    .item-label {
        font-size: 14px;
        font-weight: bold;
        line-height: 1.1;
    }
    
    /* Estilo do Preço */
    .price-label {
        font-size: 12px;
        color: #666;
    }

    /* Barra de total fixa e menor */
    .total-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: #ff6600;
        color: white;
        text-align: center;
        padding: 10px;
        font-size: 18px;
        font-weight: bold;
        z-index: 999;
    }
    
    /* Remover espaços extras do Streamlit */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    div[data-testid="stVerticalBlock"] > div { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# ===== NAVEGAÇÃO =====
with st.sidebar:
    st.title("🔥 Brava Brasa")
    menu = st.radio("Menu", ["Mesas / Pedidos", "Relatório", "Preços"])

if menu == "Relatório": st.session_state.pagina = "relatorio"
elif menu == "Preços": st.session_state.pagina = "precos"
else: 
    if st.session_state.pagina not in ["pedido"]: st.session_state.pagina = "mesas"

# =========================
# PÁGINA: MESAS
# =========================
if st.session_state.pagina == "mesas":
    st.subheader("🍽️ Mesas Ativas")
    lista_mesas = [f"Mesa {i}" for i in range(1, 13)]
    cols_mesas = st.columns(3) # 3 colunas de mesas para caber mais
    for i, nome in enumerate(lista_mesas):
        with cols_mesas[i % 3]:
            itens_mesa = st.session_state.pedidos_ativos.get(nome, {})
            ocupada = any(v > 0 for v in itens_mesa.values())
            cor = "#ff4b4b" if ocupada else "#28a745"
            if st.button(nome, key=f"btn_{nome}"):
                if nome not in st.session_state.pedidos_ativos:
                    st.session_state.pedidos_ativos[nome] = {item: 0 for cat in CARDAPIO_ESTRUTURA.values() for item in cat}
                st.session_state.mesa_atual = nome
                st.session_state.pagina = "pedido"
                st.rerun()

# =========================
# PÁGINA: PEDIDO (CARDÁPIO COMPACTO)
# =========================
elif st.session_state.pagina == "pedido":
    mesa = st.session_state.mesa_atual
    
    col_v, col_f = st.columns([1, 1])
    with col_v:
        if st.button("⬅️ Voltar"):
            st.session_state.pagina = "mesas"
            st.rerun()
    with col_f:
        total_atual = sum(st.session_state.pedidos_ativos[mesa][i] * precos.get(i, 0) for i in st.session_state.pedidos_ativos[mesa])
        if total_atual > 0:
            if st.button("✅ Fechar"):
                agora = datetime.now(BRASIL)
                pedido_final = {
                    "mesa": mesa,
                    "itens": {k: v for k, v in st.session_state.pedidos_ativos[mesa].items() if v > 0},
                    "total": total_atual, "data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M")
                }
                db.collection("pedidos").add(pedido_final)
                db.collection("pedidos_pendentes").document(mesa).delete()
                del st.session_state.pedidos_ativos[mesa]
                st.session_state.pagina = "mesas"
                st.rerun()

    st.write(f"### {mesa}")
    tab_esp, tab_beb = st.tabs(["🍢 ESPETINHOS", "🥤 BEBIDAS"])

    def render_compacto(lista_itens):
        for item in lista_itens:
            valor = precos.get(item, 0.0)
            qtd = st.session_state.pedidos_ativos[mesa].get(item, 0)
            
            # Layout de linha única: Nome(2) | -(1) | Qtd(1) | +(1)
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            with c1:
                st.markdown(f'<div class="item-label">{item}</div><div class="price-label">R$ {valor:.2f}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("➖", key=f"sub_{item}"):
                    if st.session_state.pedidos_ativos[mesa][item] > 0:
                        st.session_state.pedidos_ativos[mesa][item] -= 1
                        salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                        st.rerun()
            with c3:
                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:18px;'>{qtd}</div>", unsafe_allow_html=True)
            with c4:
                if st.button("➕", key=f"add_{item}"):
                    st.session_state.pedidos_ativos[mesa][item] += 1
                    salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                    st.rerun()
            st.divider()

    with tab_esp: render_compacto(CARDAPIO_ESTRUTURA["🍢 ESPETINHOS"])
    with tab_beb: render_compacto(CARDAPIO_ESTRUTURA["🥤 BEBIDAS"])

    st.markdown(f"<div class='total-bar'>TOTAL: R$ {total_atual:.2f}</div>", unsafe_allow_html=True)
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
            del st.session_state.pedidos_ativos[mesa]
            st.success("Salvo!")
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
        total_dia = sum(v['total'] for v in vendas)
        st.metric("Total Vendido", f"R$ {total_dia:.2f}")
        for v in vendas:
            with st.expander(f"{v['hora']} - {v['mesa']} | R$ {v['total']:.2f}"):
                for item, qtd in v['itens'].items():
                    st.write(f"{qtd}x {item}")
    else:
        st.info("Sem vendas.")

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
