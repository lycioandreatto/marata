import streamlit as st

if str(st.secrets.get("RUN_SUPABASE_TEST", "0")) == "1":
    import teste_supabase  # precisa existir teste_supabase.py
    raise SystemExit


@st.cache_resource
def get_engine():
    cfg = st.secrets["postgres"]
    url = (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )
    return create_engine(url, pool_pre_ping=True)

st.title("✅ Teste de conexão Supabase")

try:
    eng = get_engine()
    with eng.connect() as conn:
        qtd = conn.execute(text("select count(*) from faturado_raw;")).scalar()
        st.success(f"Conectou! Linhas em faturado_raw: {qtd}")

        df = pd.read_sql(text("select * from faturado_raw limit 50;"), conn)
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("❌ Não conectou ou não leu a tabela.")
    st.code(str(e))
