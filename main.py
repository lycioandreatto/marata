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

# ===== FUNÇÕES DE DADOS E PERSISTÊNCIA =====

def carregar_precos():
    """Busca preços do Firebase ou define padrão"""
    precos_padrao = {
        "CARNE": 8, "FRANGO": 7, "CALABRESA": 7, "CORAÇÃO": 8, 
        "QUEIJO": 6, "MISTO": 9, "COCA": 6, "GUARANA": 6, "HEINEKEN": 10
    }
    try:
        docs = db.collection("precos").stream()
        carregados = {doc.id: doc.to_dict().get("valor", 0) for doc in docs}
        for item, valor in precos_padrao.items():
            if item not in carregados:
                carregados[item] = valor
                db.collection("precos").document(item).set({"valor": valor})
        return carregados
    except:
        return precos_padrao

def salvar_rascunho_firebase(mesa, itens):
    """Salva o estado da mesa no Firebase (evita perda no F5)"""
    itens_filtrados = {k: v for k, v in itens.items() if v > 0}
    if itens_filtrados:
        db.collection("pedidos_pendentes").document(mesa).set({"itens": itens_filtrados})
    else:
        db.collection("pedidos_pendentes").document(mesa).delete()

def carregar_rascunhos_firebase():
    """Recupera mesas em aberto do Firebase ao iniciar o app"""
    docs = db.collection("pedidos_pendentes").stream()
    return {doc.id: doc.to_dict().get("itens", {}) for doc in docs}

# ===== INICIALIZAÇÃO DE ESTADO =====
BRASIL = pytz.timezone("America/Sao_Paulo")
precos = carregar_precos()

# Sincroniza rascunhos do Firebase para o Session State
if "pedidos_ativos" not in st.session_state:
    rascunhos = carregar_rascunhos_firebase()
    # Preenche dicionário com todos os itens possíveis
    for mesa in rascunhos:
        base = {item: 0 for item in precos}
        base.update(rascunhos[mesa])
        rascunhos[mesa] = base
    st.session_state.pedidos_ativos = rascunhos

if "pagina" not in st.session_state: st.session_state.pagina = "mesas"
if "mesa_atual" not in st.session_state: st.session_state.mesa_atual = None

# ===== ESTILO CSS =====
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; }
    .card-mesa { padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
    .total-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: #ff6600; color: white; 
                 text-align: center; padding: 15px; font-size: 22px; font-weight: bold; z-index: 999; }
</style>
""", unsafe_allow_html=True)

# ===== NAVEGAÇÃO LATERAL =====
with st.sidebar:
    st.title("🔥 Brava Brasa")
    menu = st.radio("Menu", ["Mesas / Pedidos", "Relatório Detalhado", "Ajustar Preços"])

if menu == "Relatório Detalhado": st.session_state.pagina = "relatorio"
elif menu == "Ajustar Preços": st.session_state.pagina = "precos"
else: 
    if st.session_state.pagina not in ["pedido"]: st.session_state.pagina = "mesas"

# =========================
# PÁGINA: GESTÃO DE MESAS
# =========================
if st.session_state.pagina == "mesas":
    st.header("🪑 Mesas")
    lista_mesas = [f"Mesa {i}" for i in range(1, 11)]
    
    cols = st.columns(2)
    for i, nome in enumerate(lista_mesas):
        with cols[i % 2]:
            # Lógica de Ocupação: Verifica se há itens > 0 no state
            itens_mesa = st.session_state.pedidos_ativos.get(nome, {})
            ocupada = any(v > 0 for v in itens_mesa.values())
            
            cor = "#ff4b4b" if ocupada else "#28a745"
            status_txt = "🔴 Ocupada" if ocupada else "🟢 Livre"
            
            st.markdown(f'<div class="card-mesa" style="border: 2px solid {cor};"><h3>{nome}</h3><p>{status_txt}</p></div>', unsafe_allow_html=True)
            
            if st.button(f"Acessar {nome}", key=f"btn_{nome}"):
                if nome not in st.session_state.pedidos_ativos:
                    st.session_state.pedidos_ativos[nome] = {item: 0 for item in precos}
                st.session_state.mesa_atual = nome
                st.session_state.pagina = "pedido"
                st.rerun()

# =========================
# PÁGINA: LANÇAMENTO DE PEDIDO
# =========================
elif st.session_state.pagina == "pedido":
    mesa = st.session_state.mesa_atual
    st.header(f"📝 Pedido: {mesa}")
    
    if st.button("⬅️ Voltar"):
        # Limpa a mesa se não houver itens ao sair
        if not any(v > 0 for v in st.session_state.pedidos_ativos[mesa].values()):
            if mesa in st.session_state.pedidos_ativos:
                del st.session_state.pedidos_ativos[mesa]
                db.collection("pedidos_pendentes").document(mesa).delete()
        st.session_state.pagina = "mesas"
        st.rerun()

    st.divider()
    
    # Lista de Itens (Cardápio)
    for item, valor in precos.items():
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        qtd = st.session_state.pedidos_ativos[mesa].get(item, 0)
        
        with c1: st.markdown(f"**{item}**\nR$ {valor:.2f}")
        with c2:
            if st.button("➕", key=f"add_{item}"):
                st.session_state.pedidos_ativos[mesa][item] += 1
                salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                st.rerun()
        with c3: st.markdown(f"### {qtd}")
        with c4:
            if st.button("➖", key=f"sub_{item}"):
                if st.session_state.pedidos_ativos[mesa][item] > 0:
                    st.session_state.pedidos_ativos[mesa][item] -= 1
                    salvar_rascunho_firebase(mesa, st.session_state.pedidos_ativos[mesa])
                    st.rerun()

    # Cálculo do Total
    total = sum(st.session_state.pedidos_ativos[mesa][i] * precos[i] for i in precos)
    st.markdown(f"<div class='total-bar'>TOTAL: R$ {total:.2f}</div>", unsafe_allow_html=True)
    st.write("\n\n\n")

    if total > 0:
        if st.button("✅ ENCERRAR CONTA E SALVAR", use_container_width=True):
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
            st.success("Pedido salvo com sucesso!")
            st.session_state.pagina = "mesas"
            st.rerun()

# =========================
# PÁGINA: RELATÓRIO
# =========================
elif st.session_state.pagina == "relatorio":
    st.header("📊 Vendas Realizadas")
    data_sel = st.date_input("Filtrar por data", datetime.now(BRASIL))
    data_str = data_sel.strftime("%Y-%m-%d")
    
    # Consulta Firebase (Necessário índice composto se usar order_by)
    # Para evitar erros de índice, ordenamos no Python
    pedidos_ref = db.collection("pedidos").where("data", "==", data_str).stream()
    lista_pedidos = sorted([p.to_dict() for p in pedidos_ref], key=lambda x: x['hora'], reverse=True)
    
    if lista_pedidos:
        df = pd.DataFrame(lista_pedidos)
        st.metric("Faturamento do Dia", f"R$ {df['total'].sum():.2f}")
        
        for p in lista_pedidos:
            with st.expander(f"🕒 {p['hora']} - {p['mesa']} | Total: R$ {p['total']:.2f}"):
                dados_itens = []
                for item, qtd in p.get("itens", {}).items():
                    p_unit = precos.get(item, 0)
                    dados_itens.append({"Item": item, "Qtd": qtd, "Subtotal": f"R$ {qtd*p_unit:.2f}"})
                st.table(pd.DataFrame(dados_itens))
    else:
        st.info("Nenhum pedido finalizado nesta data.")

# =========================
# PÁGINA: PREÇOS
# =========================
elif st.session_state.pagina == "precos":
    st.header("⚙️ Ajustar Cardápio")
    for item, valor in precos.items():
        novo_v = st.number_input(f"Preço: {item}", value=float(valor), step=0.5, key=f"prc_{item}")
        if novo_v != float(valor):
            db.collection("precos").document(item).set({"valor": novo_v})
            st.toast(f"Atualizado: {item}")
