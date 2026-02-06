import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

def run():
    st.set_page_config(page_title="Teste Supabase", layout="wide")
    st.title("✅ Teste de conexão Supabase")

    cfg = st.secrets["postgres"]

    # Debug pra ver o host real vindo do Secrets
    st.write("HOST RAW:", repr(cfg["host"]))
    st.write("PORT:", cfg["port"])
    st.write("USER:", cfg["user"])

    url = URL.create(
        "postgresql+psycopg2",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=int(cfg["port"]),
        database=cfg["dbname"],
    )

    try:
        eng = create_engine(url, pool_pre_ping=True, connect_args={"sslmode": "require"})
        with eng.connect() as conn:
            qtd = conn.execute(text("select count(*) from faturado_raw;")).scalar()
            st.success(f"Conectou! Linhas em faturado_raw: {qtd}")

            df = pd.read_sql(text("select * from faturado_raw limit 50;"), conn)
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error("❌ Não conectou ou não leu a tabela.")
        st.code(str(e))
