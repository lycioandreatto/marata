import streamlit as st
import urllib.parse

# CONFIG
st.set_page_config(page_title="Match do Espeto", page_icon="🔥", layout="wide")

# ESTILO
st.markdown("""
<style>
.stApp {
    background-color: #000000;
    color: white;
}

h1,h2,h3 {
    color: #ff2e8a;
}

button {
    background-color:#ff2e8a !important;
    color:white !important;
}

.item-box {
    background-color:#111;
    padding:15px;
    border-radius:10px;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# LOGO / TÍTULO
st.title("🔥 MATCH DO ESPETO")
st.subheader("Encontro Perfeito do Sabor")

# CARDÁPIO
cardapio = {
    "Espeto de Carne": 8,
    "Espeto de Frango": 7,
    "Espeto de Linguiça": 7,
    "Queijo Coalho": 9,
    "Coca Cola Lata": 5,
    "Guaraná": 5,
    "Água": 3
}

# CARRINHO
if "carrinho" not in st.session_state:
    st.session_state.carrinho = {}

st.header("🍢 Cardápio")

for item, preco in cardapio.items():
    col1, col2, col3 = st.columns([3,1,1])

    with col1:
        st.write(f"**{item}**")
        st.write(f"R$ {preco}")

    with col2:
        if st.button(f"Adicionar {item}"):
            if item in st.session_state.carrinho:
                st.session_state.carrinho[item] += 1
            else:
                st.session_state.carrinho[item] = 1

    with col3:
        if item in st.session_state.carrinho:
            st.write(f"x{st.session_state.carrinho[item]}")

# CARRINHO
st.header("🛒 Seu Pedido")

total = 0
pedido_texto = ""

for item, qtd in st.session_state.carrinho.items():
    preco = cardapio[item]
    subtotal = preco * qtd
    total += subtotal

    st.write(f"{qtd}x {item} - R$ {subtotal}")
    pedido_texto += f"{qtd}x {item} - R$ {subtotal}\n"

st.subheader(f"Total: R$ {total}")

# DADOS CLIENTE
st.header("📍 Dados para entrega")

nome = st.text_input("Nome")
telefone = st.text_input("Telefone")
endereco = st.text_input("Endereço")
obs = st.text_area("Observação")

pagamento = st.selectbox(
    "Forma de pagamento",
    ["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"]
)

# BOTÃO WHATSAPP
if st.button("📲 Enviar pedido no WhatsApp"):

    numero = "5579998439298"

    mensagem = f"""
Pedido - Match do Espeto 🔥

Cliente: {nome}
Telefone: {telefone}

Itens:
{pedido_texto}

Total: R$ {total}

Pagamento: {pagamento}

Endereço:
{endereco}

Observação:
{obs}
"""

    mensagem_codificada = urllib.parse.quote(mensagem)

    link = f"https://wa.me/{numero}?text={mensagem_codificada}"

    st.markdown(f"[Clique aqui para enviar seu pedido]({link})")
