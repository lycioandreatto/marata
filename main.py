import streamlit as st
import json
from datetime import datetime
import os
import pandas as pd
import pytz  # para timezone

import firebase_admin
from firebase_admin import credentials, firestore

# ===== FIREBASE =====
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def salvar_pedido(pedido):
    db.collection("pedidos").add(pedido)

# ===== PREÇOS FIREBASE =====
def carregar_precos_firebase():
    """Carrega preços do Firebase. Se não existir, cria com valores padrão."""
    precos_ref = db.collection("precos")
    docs = precos_ref.stream()
    precos_carregados = {}
    for doc in docs:
        precos_carregados[doc.id] = doc.to_dict().get("valor", 0)
    # adiciona itens que não existirem
    for item, valor in precos_padrao.items():
        if item not in precos_carregados:
            precos_carregados[item] = valor
            db.collection("precos").document(item).set({"valor": valor})
    return precos_carregados

def salvar_preco_firebase(item, valor):
    db.collection("precos").document(item).set({"valor": valor})

# ===== CONFIGURAÇÃO STREAMLIT =====
st.set_page_config(page_title="Brava Brasa", page_icon="🔥", layout="wide")

# ===== ESTILO =====
st.markdown("""
<style>
.stApp{background:#ffffff;font-family:sans-serif;}
.title{text-align:center;color:#ff6600;font-size:40px;font-weight:bold;}
.card{background:white;padding:15px;border-radius:15px;box-shadow:0 3px 10px rgba(0,0,0,0.1);margin-bottom:15px;text-align:center;}
button{background:#ff6600 !important;color:white !important;border-radius:8px !important;height:45px;width:100%;font-size:16px;}
.total{font-size:28px;color:#ff6600;font-weight:bold;text-align:center;}
.counter{text-align:center;color:#ff6600;font-weight:bold;font-size:20px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🔥 BRAVA BRASA</div>', unsafe_allow_html=True)

# ===== TIMEZONE BRASIL =====
BRASIL = pytz.timezone("America/Sao_Paulo")

# ===== ARQUIVO LOCAL =====
ARQUIVO = "historico.json"
def carregar_json_local():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r") as f:
            return json.load(f)
    return []

def salvar_json_local(dados):
    with open(ARQUIVO, "w") as f:
        json.dump(dados, f)

# ===== PREÇOS PADRÃO =====
precos_padrao = {"CARNE":8,"FRANGO":7,"CALABRESA":7,"CORAÇÃO":8,"QUEIJO":6,"MISTO":9,"COCA":6,"GUARANA":6,"HEINEKEN":10}

# ===== CARREGA PREÇOS DO FIREBASE =====
precos = carregar_precos_firebase()

def nova_mesa():
    return {"itens": {i:0 for i in precos}, "fechado": False, "iniciado": False}

# ===== ESTADO =====
if "mesas" not in st.session_state:
    st.session_state.mesas = {}
if "mesa_aberta" not in st.session_state:
    st.session_state.mesa_aberta = {}
if "pagina" not in st.session_state:
    st.session_state.pagina = "mesas"
if "mesa_atual" not in st.session_state:
    st.session_state.mesa_atual = None
if "historico" not in st.session_state:
    historico = carregar_json_local()
    pedidos_firebase = db.collection("pedidos").stream()
    for doc in pedidos_firebase:
        p = doc.to_dict()
        # garante itens padronizados
        itens_padronizados = {item: p.get("itens", {}).get(item, 0) for item in precos}
        p["itens"] = itens_padronizados
        if p not in historico:
            historico.append(p)
    st.session_state.historico = historico
if "pedido_detalhe" not in st.session_state:
    st.session_state.pedido_detalhe = None

# =========================
# BOTÃO RELATÓRIO
# =========================
if st.session_state.pagina != "relatorio":
    if st.button("📊 Relatório"):
        st.session_state.pagina = "relatorio"

# =========================
# MESAS
# =========================
if st.session_state.pagina == "mesas":
    st.subheader("🪑 Mesas")
    st.markdown(f'<div class="counter">Pedidos salvos hoje: {len(st.session_state.historico)}</div>', unsafe_allow_html=True)

    # Botão para ajustar preços
    with st.expander("⚙️ Ajustar preços"):
        for item in precos:
            novo_valor = st.number_input(f"{item}", min_value=0, value=precos[item], step=1)
            if novo_valor != precos[item]:
                precos[item] = novo_valor
                salvar_preco_firebase(item, novo_valor)
                st.success(f"Preço de {item} atualizado para R$ {novo_valor}")

    mesas = ["Mesa 1","Mesa 2","Mesa 3","Mesa 4"]
    for i in range(0, len(mesas), 2):
        cols = st.columns(2)
        for j in range(2):
            if i+j < len(mesas):
                mesa = mesas[i+j]
                status = "🔴 Ocupada" if st.session_state.mesas.get(mesa, {}).get("iniciado", False) else "🟢 Livre"
                with cols[j]:
                    st.markdown(f'<div class="card"><h2>{mesa}</h2><p>{status}</p></div>', unsafe_allow_html=True)
                    if st.button(f"Acessar {mesa}", key=f"acessar_{mesa}"):
                        if mesa not in st.session_state.mesas:
                            st.session_state.mesas[mesa] = nova_mesa()
                        st.session_state.mesa_atual = mesa
                        st.session_state.pagina = "pedido"

# =========================
# PEDIDO
# =========================
elif st.session_state.pagina == "pedido":
    mesa = st.session_state.mesa_atual
    pedido = st.session_state.mesas[mesa]

    st.subheader(f"📋 {mesa}")

    if not pedido["iniciado"]:
        st.info("📌 Pedido não iniciado")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 Abrir Pedido"):
                st.session_state.mesas[mesa]["iniciado"] = True
                st.success("Pedido iniciado! Agora você pode adicionar itens.")
        with col2:
            if st.button("⬅️ Voltar"):
                st.session_state.pagina = "mesas"
    else:
        if pedido["fechado"]:
            st.error("🔒 Pedido FECHADO")
        else:
            st.success("🟢 Pedido ABERTO")

        st.divider()
        st.subheader("🍢 Itens")
        cols = st.columns(3)
        for i,item in enumerate(precos):
            with cols[i%3]:
                if st.button(item, key=f"{item}_{mesa}") and not pedido["fechado"]:
                    st.session_state.mesas[mesa]["itens"][item] += 1

        st.divider()
        total = sum(qtd*precos[item] for item,qtd in pedido["itens"].items() if qtd>0)
        for item,qtd in pedido["itens"].items():
            if qtd>0:
                valor = qtd * precos[item]
                col1,col2,col3 = st.columns([4,1,1])
                with col1: st.write(f"{item} x{qtd}")
                with col2: st.write(f"R$ {valor}")
                with col3:
                    if st.button("➖",key=f"menos_{item}_{mesa}") and not pedido["fechado"]:
                        st.session_state.mesas[mesa]["itens"][item] -= 1

        st.markdown(f"<div class='total'>Total: R$ {total}</div>",unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            if not pedido["fechado"]:
                if st.button("🔒 Fechar", key=f"fechar_{mesa}"):
                    st.session_state.mesas[mesa]["fechado"] = True
            elif pedido["fechado"]:
                if st.button("🔓 Reabrir", key=f"reabrir_{mesa}"):
                    st.session_state.mesas[mesa]["fechado"] = False
        with col2:
            if st.button("❌ Encerrar", key=f"encerrar_{mesa}"):
                agora = datetime.now(BRASIL)
                novo = {
                    "mesa": mesa,
                    "itens": pedido["itens"],
                    "total": total,
                    "data": agora.strftime("%Y-%m-%d"),
                    "hora": agora.strftime("%H:%M")
                }
                st.session_state.historico.append(novo)
                salvar_json_local(st.session_state.historico)
                salvar_pedido(novo)
                st.success("✅ Pedido salvo no Firebase!")
                st.json(novo)
                del st.session_state.mesas[mesa]
                st.session_state.pagina = "mesas"
        with col3:
            if st.button("⬅️ Voltar", key=f"voltar_{mesa}"):
                st.session_state.pagina = "mesas"

# =========================
# RELATÓRIO
# =========================
elif st.session_state.pagina == "relatorio":
    st.title("📊 Relatório")
    if st.button("⬅️ Voltar"): st.session_state.pagina = "mesas"

    # Atualiza pedidos do Firebase
    st.session_state.historico = [doc.to_dict() for doc in db.collection("pedidos").stream()]

    hoje = datetime.now(BRASIL).strftime("%Y-%m-%d")
    pedidos = [p for p in st.session_state.historico if p["data"] == hoje]
    total = sum(p["total"] for p in pedidos)
    st.subheader(f"💰 Total do dia: R$ {total}")
    if pedidos:
        df = pd.DataFrame(pedidos)
        st.bar_chart(df["total"])
    
    st.divider()
    st.subheader("📋 Pedidos")
    for i, pedido in enumerate(pedidos):
        if st.button(f"{pedido['hora']} - {pedido['mesa']} - R$ {pedido['total']}", key=f"hist{i}"):
            st.session_state.pedido_detalhe = pedido
            st.session_state.pagina = "detalhe"

# =========================
# DETALHE
# =========================
elif st.session_state.pagina == "detalhe":
    pedido = st.session_state.pedido_detalhe
    st.title(f"📋 {pedido['mesa']}")
    for item,qtd in pedido["itens"].items():
        if qtd>0: st.write(f"{item} x{qtd} - R$ {qtd*precos[item]}")
    st.subheader(f"💰 Total: R$ {pedido['total']}")
    if st.button("⬅️ Voltar"): st.session_state.pagina = "relatorio"
