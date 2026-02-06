# teste_supabase.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

def run():
    st.set_page_config(page_title="Teste Supabase", layout="wide")
    st.title("✅ Teste de conexão Supabase (Pooler)")

    # Lê configs do Secrets
    cfg = st.secrets["postgres"]

    # Debug (pra você ver exatamente o que o app está usando)
    st.write("HOST RAW:", repr(cfg.get("host")))
    st.write("PORT:", cfg.get("port"))
    st.write("DBNAME:", cfg.get("dbname"))
    st.write("USER:", cfg.get("user"))

    # Monta URL de conexão com segurança (evita quebrar por caracteres na senha)
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=int(cfg["port"]),
        database=cfg["dbname"],
    )

    try:
        # Importante para pooler/pgbouncer: NÃO reutilizar conexões (evita SSL closed unexpectedly)
        engine = create_engine(
            url,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={"sslmode": "require"},
        )

        with engine.connect() as conn:
            # Teste 1: contar linhas
            qtd = conn.execute(text("select count(*) from faturado_raw;")).scalar()
            st.success(f"Conectou! Linhas em faturado_raw: {qtd}")

            # Teste 2: puxar amostra
            df = pd.read_sql(text("select * from faturado_raw limit 50;"), conn)
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error("❌ Não conectou ou não leu a tabela.")
        st.code(str(e))

# Se você abrir esse arquivo direto (não via main.py), ele roda sozinho também
if __name__ == "__main__":
    run()
