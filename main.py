import streamlit as st
import json
from datetime import datetime
import os
import pandas as pd

st.set_page_config(page_title="Brava Brasa", page_icon="🔥", layout="wide")

# 🎨 ESTILO
st.markdown("""
<style>
.stApp{
background:#f3f3f3;
font-family:sans-serif;
}

.title{
text-align:center;
color:#ff2e8a;
font-size:40px;
font-weight:bold;
}

.card{
background:white;
padding:15px;
border-radius:15px;
box-shadow:0 3px 10px rgba(0,0,0,0.1);
margin-bottom:15px;
text-align:center;
}

button{
background:#ff2e8a !important;
color:white !important;
border-radius:8px !important;
height:60px;
width:100%;
}

.total{
font-size:28px;
color:#ff2e8a;
font-weight:bold;
text-align:center;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🔥 BRAVA BRASA</div>', unsafe_allow_html=True)

# ===== ARQUIVO =====
ARQUIVO = "historico.json"

def carregar():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r") as f:
            return json.load(f)
    return []

def salvar(dados):
    with open(ARQUIVO, "w") as f:
        json.dump(dados, f)

# ===== ESTADO =====
if "mesas" not in st.session_state:
    st.session_state.mesas = {}

if "pagina" not in st.session_state:
    st.session_state.pagina = "mesas"

if "mesa_atual" not in st.session_state:
    st.session_state.mesa_atual = None

if "historico" not in st.session_state:
    st.session_state.historico = carregar()

if "pedido_detalhe" not in st.session_state:
    st.session_state.pedido_detalhe = None

# ===== PREÇOS =====
precos = {
    "CARNE": 8,
    "FRANGO": 7,
    "CALABRESA": 7,
    "CORAÇÃO": 8,
    "QUEIJO": 6,
    "MISTO": 9,
    "COCA": 6,
    "GUARANA": 6,
    "HEINEKEN": 10
}

def nova_mesa():
    return {"itens": {i:0 for i in precos}, "fechado": False}

# =========================
# BOTÃO RELATÓRIO
# =========================
if st.button("📊 Relatório"):
    st.session_state.pagina = "relatorio"

# =========================
# MESAS
# =========================
if st.session_state.pagina == "mesas":

    st.subheader("🪑 Mesas")

    mesas = ["Mesa 1","Mesa 2","Mesa 3","Mesa 4"]
    cols = st.columns(2)

    for i,mesa in enumerate(mesas):
        with cols[i%2]:

            status = "🔴 Ocupada" if mesa in st.session_state.mesas else "🟢 Livre"

            st.markdown(f"""
            <div class="card">
                <h2>{mesa}</h2>
                <p>{status}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Acessar {mesa}", key=mesa):
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

    st.divider()

    st.subheader("🍢 Itens")

    cols = st.columns(3)

    for i,item in enumerate(precos):
        with cols[i%3]:
            if st.button(item):
                pedido["itens"][item]+=1

    st.divider()

    total = 0

    for item,qtd in pedido["itens"].items():
        if qtd>0:
            valor = qtd*precos[item]
            total+=valor

            col1,col2,col3=st.columns([4,1,1])

            with col1:
                st.write(f"{item} x{qtd}")
            with col2:
                st.write(f"R$ {valor}")
            with col3:
                if st.button("➖",key=f"{item}{mesa}"):
                    pedido["itens"][item]-=1

    st.markdown(f"<div class='total'>Total: R$ {total}</div>",unsafe_allow_html=True)

    col1,col2,col3=st.columns(3)

    with col1:
        if st.button("🔒 Fechar"):
            pedido["fechado"]=True

    with col2:
        if st.button("❌ Encerrar"):

            novo = {
                "mesa": mesa,
                "itens": pedido["itens"],
                "total": total,
                "data": datetime.now().strftime("%Y-%m-%d"),
                "hora": datetime.now().strftime("%H:%M")
            }

            st.session_state.historico.append(novo)
            salvar(st.session_state.historico)

            del st.session_state.mesas[mesa]
            st.session_state.pagina="mesas"
            st.rerun()

    with col3:
        if st.button("⬅️ Voltar"):
            st.session_state.pagina="mesas"

# =========================
# RELATÓRIO
# =========================
elif st.session_state.pagina == "relatorio":

    st.title("📊 Relatório")

    if st.button("⬅️ Voltar"):
        st.session_state.pagina = "mesas"

    hoje = datetime.now().strftime("%Y-%m-%d")

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
# DETALHE DO PEDIDO
# =========================
elif st.session_state.pagina == "detalhe":

    pedido = st.session_state.pedido_detalhe

    st.title(f"📋 {pedido['mesa']}")

    for item, qtd in pedido["itens"].items():
        if qtd > 0:
            valor = qtd * precos[item]
            st.write(f"{item} x{qtd} - R$ {valor}")

    st.subheader(f"💰 Total: R$ {pedido['total']}")

    if st.button("⬅️ Voltar"):
        st.session_state.pagina = "relatorio"
