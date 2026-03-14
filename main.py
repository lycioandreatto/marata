import streamlit as st
import urllib.parse

st.set_page_config(page_title="Match do Espeto", page_icon="🔥", layout="centered")

# ESTILO
st.markdown("""
<style>

.stApp{
background-color:#000000;
color:white;
}

h1{
color:#ff2e8a;
text-align:center;
}

.card{
background:#111;
padding:15px;
border-radius:12px;
margin-bottom:15px;
}

.stButton>button{
background-color:#ff2e8a;
color:white;
border-radius:10px;
border:none;
padding:10px 15px;
font-weight:bold;
}

.total{
font-size:22px;
color:#ff2e8a;
}

</style>
""", unsafe_allow_html=True)

st.title("🔥 MATCH DO ESPETO")
st.write("### Encontro Perfeito do Sabor")

# CARDÁPIO
menu = {
"Espeto de Carne":8,
"Espeto de Frango":7,
"Espeto de Linguiça":7,
"Queijo Coalho":9,
"Coca Cola":5,
"Guaraná":5,
"Água":3
}

if "cart" not in st.session_state:
    st.session_state.cart={}

st.header("🍢 Cardápio")

for item,price in menu.items():

    st.markdown(f'<div class="card">',unsafe_allow_html=True)

    col1,col2,col3=st.columns([3,1,1])

    with col1:
        st.write(f"**{item}**")
        st.write(f"R$ {price}")

    with col2:
        if st.button("+",key=item):
            st.session_state.cart[item]=st.session_state.cart.get(item,0)+1

    with col3:
        if item in st.session_state.cart:
            st.write(f"x{st.session_state.cart[item]}")
        else:
            st.write("0")

    st.markdown("</div>",unsafe_allow_html=True)

st.header("🛒 Seu Pedido")

total=0
pedido=""

for item,qtd in st.session_state.cart.items():
    subtotal=menu[item]*qtd
    total+=subtotal
    pedido+=f"{qtd}x {item} - R$ {subtotal}\n"
    st.write(f"{qtd}x {item} - R$ {subtotal}")

st.markdown(f"<p class='total'>Total: R$ {total}</p>",unsafe_allow_html=True)

st.header("📍 Entrega")

nome=st.text_input("Nome")
telefone=st.text_input("Telefone")
endereco=st.text_input("Endereço")
obs=st.text_area("Observação")

pagamento=st.selectbox(
"Forma de pagamento",
["PIX","Dinheiro","Cartão de Crédito","Cartão de Débito"]
)

numero="5579998439298"

mensagem=f"""
🔥 Pedido - Match do Espeto

Cliente: {nome}
Telefone: {telefone}

Itens:
{pedido}

Total: R$ {total}

Pagamento: {pagamento}

Endereço:
{endereco}

Obs:
{obs}
"""

link=f"https://wa.me/{numero}?text={urllib.parse.quote(mensagem)}"

st.markdown(
f'<a href="{link}" target="_blank"><button style="width:100%;height:50px;background:#ff2e8a;color:white;border:none;border-radius:10px;font-size:18px;">📲 Enviar Pedido no WhatsApp</button></a>',
unsafe_allow_html=True
)
