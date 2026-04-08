import streamlit as st
import json
from datetime import datetime
import os
import pandas as pd
import pytz
import firebase_admin
from firebase_admin import credentials, firestore

# ===== CONFIGURAÇÃO STREAMLIT =====
st.set_page_config(page_title="Brava Brasa", page_icon="🔥", layout="wide")

# ===== FIREBASE =====
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ===== FUNÇÕES DE PERSISTÊNCIA =====

def carregar_precos():
    precos_ref = db.collection("precos").stream()
    precos = {doc.id: doc.to_dict().get("valor", 0) for doc in precos_ref}
    return precos

def salvar_rascunho_firebase(mesa, itens):
    """Salva o estado atual da mesa no Firebase para não perder no F5"""
    # Remove itens com quantidade zero para economizar espaço
    itens_filtrados = {k: v for k, v in itens.items() if v > 0}
    if itens_filtrados:
        db.collection("pedidos_pendentes").document(mesa).set({"itens": itens_filtrados})
    else:
        # Se não tem itens, remove o documento (mesa fica livre)
        db.collection("pedidos_pendentes").document(mesa).delete()

def carregar_todos_rascunhos():
    """Busca todas as mesas que têm pedidos em aberto no Firebase"""
    docs = db.collection("pedidos_pendentes").stream()
    return {doc.id: doc.to_dict().get("itens", {}) for doc in docs}

# ===== INICIALIZAÇÃO =====
BRASIL = pytz.timezone("America/Sao_Paulo")
precos = carregar_precos()

# Sincroniza o que está no Firebase com o Session State ao iniciar/recarregar
if "pedidos_ativos" not in st.session_state:
    rascunhos = carregar_todos_rascunhos()
    # Garante que todas as chaves de itens existam para cada mesa carregada
    for mesa in rascunhos:
        full_itens = {item: 0 for item in precos}
        full_itens.update(rascunhos[mesa])
        rascunhos[mesa] = full_itens
    st.session_state.pedidos_ativos = rascunhos

if "pagina" not in st.session_state: st.session_state.pagina = "mesas"
if "mesa_selecionada" not in st.session_state: st.session_state.mesa_selecionada = None

# =========================
# PÁGINA: GESTÃO DE MESAS
# =========================
if st.session_state.pagina == "mesas":
    st.header("🪑 Mesas")
    mesas_disponiveis = [f"Mesa {i}" for i in range(1, 11)]
    
    cols = st.columns(2)
    for idx, nome_mesa in enumerate(mesas_disponiveis):
        with cols[idx % 2]:
            # Uma mesa só é "Ocupada" (Vermelha) se tiver itens > 0 no Firebase/State
            itens_da_mesa = st.session_state.pedidos_ativos.get(nome_mesa, {})
            esta_ocupada = any(v > 0 for v in itens_da_mesa.values())
            
            cor_status = "🔴 Ocupada" if esta_ocupada else "🟢 Livre"
            st.markdown(f"""<div style="padding:15px; border-radius:10px; border:2px solid {'#ff4b4b' if esta_ocupada else '#28a745'}; text-align:center;">
                        <h3>{nome_mesa}</h3><p>{cor_status}</p></div>""", unsafe_allow_html=True)
            
            if st.button(f"Selecionar {nome_mesa}", key=f"sel_{nome_mesa}"):
                if nome_mesa not in st.session_state.pedidos_ativos:
                    st.session_state.pedidos_ativos[nome_mesa] = {item: 0 for item in precos}
                st.session_state.mesa_selecionada = nome_mesa
                st.session_state.pagina = "pedido"
                st.rerun()

# =========================
# PÁGINA: LANÇAR PEDIDO
# =========================
elif st.session_state.pagina == "pedido":
    mesa = st.session_state.mesa_selecionada
    st.subheader(f"📝 Pedido: {mesa}")
    
    if st.button("⬅️ Voltar (Salva automático)"):
        # Antes de voltar, verifica se a mesa está vazia para limpá-la
        if not any(v > 0 for v in st.session_state.pedidos_ativos[mesa].values()):
            if mesa in st.session_state.pedidos_ativos:
                del st.session_state.pedidos_ativos[mesa]
                db.collection("pedidos_pendentes").document(mesa).delete()
        
        st.session_state.pagina = "mesas"
        st.rerun()

    st.divider()
    
    for item, valor in precos.items():
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        qtd = st.session_state.pedidos_ativos[mesa][item]
        
        with c1: st.write(f"**{item}** (R${valor})")
        with c2:
            if st.button("➕", key=f"add_{item}"):
                st.session_state.pedidos_ativos[mesa][item] += 1
                salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                st.rerun()
        with c3: st.write(f"**{qtd}**")
        with c4:
            if st.button("➖", key=f"sub_{item}"):
                if st.session_state.pedidos_ativos[mesa][item] > 0:
                    st.session_state.pedidos_ativos[mesa][item] -= 1
                    salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                    st.rerun()

    # Total e Finalização
    total = sum(st.session_state.pedidos_ativos[mesa][i] * precos[i] for i in precos)
    st.markdown(f"### Total: R$ {total:.2f}")

    if total > 0:
        if st.button("✅ ENCERRAR CONTA", use_container_width=True):
            agora = datetime.now(BRASIL)
            pedido_final = {
                "mesa": mesa,
                "itens": {k: v for k, v in st.session_state.pedidos_ativos[mesa].items() if v > 0},
                "total": total,
                "data": agora.strftime("%Y-%m-%d"),
                "hora": agora.strftime("%H:%M")
            }
            # 1. Salva no relatório definitivo
            db.collection("pedidos").add(pedido_final)
            # 2. Remove dos pendentes/rascunhos
            db.collection("pedidos_pendentes").document(mesa).delete()
            del st.session_state.pedidos_ativos[mesa]
            
            st.success("Pedido encerrado e salvo!")
            st.session_state.pagina = "mesas"
            st.rerun()
