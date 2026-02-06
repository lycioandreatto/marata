cfg = st.secrets["postgres"]
st.write("HOST RAW:", repr(cfg["host"]))
st.write("PORT:", cfg["port"])
st.write("USER:", cfg["user"])





import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

def run():
    st.title("✅ Teste de conexão Supabase")

    cfg = st.secrets["postgres"]
    url = (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )

    try:
        eng = create_engine(url, pool_pre_ping=True)

        with eng.connect() as conn:
            qtd = conn.execute(text("select count(*) from faturado_raw;")).scalar()
            st.success(f"Conectou! Linhas em faturado_raw: {qtd}")

            df = pd.read_sql(text("select * from faturado_raw limit 50;"), conn)
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error("❌ Não conectou ou não leu a tabela.")
        st.code(str(e))
