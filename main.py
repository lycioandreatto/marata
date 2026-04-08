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

# ===== ESTILO CSS (CORREÇÃO PARA CELULAR) =====
st.markdown("""
<style>
    /* Força colunas a ficarem lado a lado no mobile */
    [data-testid="column"] {
        display: inline-block !important;
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }
    
    /* Ajuste de botões para dedos (menores e lado a lado) */
    .stButton>button {
        width: 100% !important;
        height: 45px !important;
        padding: 0px !important;
        margin-top: 0px !important;
    }

    /* Remove espaçamentos exagerados do Streamlit */
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
    
    /* Estilo para os cards de mesa */
    .mesa-btn {
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-weight: bold;
    }

    /* Barra de total fixa */
    .total-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: #ff6600;
        color: white;
        text-align: center;
        padding: 12px;
        font-size: 20px;
        font-weight: bold;
        z-index: 999;
    }
</style>
""", unsafe_allow_html=True)

# ===== NAVEGAÇÃO =====
with st.sidebar:
    st.title("🔥 Brava Brasa")
    menu = st.radio("Menu", ["Mesas", "Relatório", "Ajustar Preços"])

if menu == "Relatório": st.session_state.pagina = "relatorio"
elif menu == "Ajustar Preços": st.session_state.pagina = "precos"
else: 
    if st.session_state.pagina not in ["pedido"]: st.session_state.pagina = "mesas"

# =========================
# PÁGINA: MESAS
# =========================
if st.session_state.pagina == "mesas":
    st.subheader("🍽️ Selecione a Mesa")
    lista_mesas = [f"Mesa {i}" for i in range(1, 13)]
    
    # Grid de 3 colunas para economizar espaço
    cols = st.columns(3)
    for i, nome in enumerate(lista_mesas):
        with cols[i % 3]:
            itens_mesa = st.session_state.pedidos_ativos.get(nome, {})
            ocupada = any(v > 0 for v in itens_mesa.values())
            # Botão muda de cor se estiver ocupada (usando ícone ou estilo)
            label = f"🔴 {nome}" if ocupada else f"🟢 {nome}"
            if st.button(label, key=f"btn_{nome}"):
                if nome not in st.session_state.pedidos_ativos:
                    st.session_state.pedidos_ativos[nome] = {item: 0 for cat in CARDAPIO_ESTRUTURA.values() for item in cat}
                st.session_state.mesa_atual = nome
                st.session_state.pagina = "pedido"
                st.rerun()

# =========================
# PÁGINA: PEDIDO (DESIGN COMPACTO)
# =========================
elif st.session_state.pagina == "pedido":
    mesa = st.session_state.mesa_atual
    
    # Cabeçalho com botões de ação rápidos
    c_voltar, c_mesa, c_finalizar = st.columns([1, 1.5, 1])
    with c_voltar:
        if st.button("⬅️"):
            st.session_state.pagina = "mesas"
            st.rerun()
    with c_mesa:
        st.markdown(f"<h3 style='text-align:center; margin:0;'>{mesa}</h3>", unsafe_allow_html=True)
    with c_finalizar:
        total = sum(st.session_state.pedidos_ativos[mesa][i] * precos.get(i, 0) for i in st.session_state.pedidos_ativos[mesa])
        if total > 0:
            if st.button("✅"):
                agora = datetime.now(BRASIL)
                db.collection("pedidos").add({
                    "mesa": mesa, "itens": {k: v for k, v in st.session_state.pedidos_ativos[mesa].items() if v > 0},
                    "total": total, "data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M")
                })
                db.collection("pedidos_pendentes").document(mesa).delete()
                del st.session_state.pedidos_ativos[mesa]
                st.session_state.pagina = "mesas"
                st.rerun()

    tab_esp, tab_beb = st.tabs(["🍢 ESPETOS", "🥤 BEBIDAS"])

    def render_itens(lista):
        for item in lista:
            val = precos.get(item, 0.0)
            qtd = st.session_state.pedidos_ativos[mesa].get(item, 0)
            
            # LINHA COMPACTA: Nome/Preço | - | Qtd | +
            col_info, col_menos, col_qtd, col_mais = st.columns([2.5, 1, 1, 1])
            with col_info:
                st.markdown(f"**{item}**<br><small>R${val:.2f}</small>", unsafe_allow_html=True)
            with col_menos:
                if st.button("➖", key=f"sub_{item}"):
                    if st.session_state.pedidos_ativos[mesa][item] > 0:
                        st.session_state.pedidos_ativos[mesa][item] -= 1
                        salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                        st.rerun()
            with col_qtd:
                st.markdown(f"<h4 style='text-align:center; margin-top:10px;'>{qtd}</h4>", unsafe_allow_html=True)
            with col_mais:
                if st.button("➕", key=f"add_{item}"):
                    st.session_state.pedidos_ativos[mesa][item] += 1
                    salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                    st.rerun()
            st.markdown("---")

    with tab_esp: render_itens(CARDAPIO_ESTRUTURA["🍢 ESPETINHOS"])
    with tab_beb: render_itens(CARDAPIO_ESTRUTURA["🥤 BEBIDAS"])

    st.markdown(f"<div class='total-bar'>TOTAL: R$ {total:.2f}</div>", unsafe_allow_html=True)

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
        st.metric("Total do Dia", f"R$ {sum(v['total'] for v in vendas):.2f}")
        for v in vendas:
            with st.expander(f"{v['hora']} - {v['mesa']} (R${v['total']:.2f})"):
                for it, q in v['itens'].items(): st.write(f"{q}x {it}")
    else: st.info("Sem vendas.")

# =========================
# PÁGINA: PREÇOS
# =========================
elif st.session_state.pagina == "precos":
    st.header("⚙️ Ajustar Preços")
    for cat, itens in CARDAPIO_ESTRUTURA.items():
        st.subheader(cat)
        for item in itens:
            v = st.number_input(f"{item}", value=float(precos.get(item, 0.0)), step=0.5, key=f"p_{item}")
            if v != precos.get(item, 0.0):
                db.collection("precos").document(item).set({"valor": v})
                st.toast(f"{item} atualizado!")
