# teste_supabase.py
import streamlit as st
import pandas as pd
import psycopg2

def run():
    st.set_page_config(page_title="Teste Supabase", layout="wide")
    st.title("✅ Teste de conexão Supabase (Pooler - psycopg2 direto)")

    cfg = st.secrets["postgres"]

    st.write("HOST RAW:", repr(cfg.get("host")))
    st.write("PORT:", cfg.get("port"))
    st.write("DBNAME:", cfg.get("dbname"))
    st.write("USER:", cfg.get("user"))

    try:
        conn = psycopg2.connect(
            host=cfg["host"],
            port=int(cfg["port"]),
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=cfg["password"],
            sslmode="require",
        )

        cur = conn.cursor()
        cur.execute("select count(*) from faturado_raw;")
        qtd = cur.fetchone()[0]
        st.success(f"Conectou! Linhas em faturado_raw: {qtd}")

        df = pd.read_sql("select * from faturado_raw limit 50;", conn)
        st.dataframe(df, use_container_width=True)

        cur.close()
        conn.close()

    except Exception as e:
        st.error("❌ Não conectou ou não leu a tabela.")
        st.code(str(e))

if __name__ == "__main__":
    run()
