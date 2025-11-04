import streamlit as st, pandas as pd, sqlite3

st.set_page_config(page_title="OpenSourceMalware – IOC Browser", layout="wide")
st.title("OpenSourceMalware – IOC Browser")

con = sqlite3.connect("iocs.db")
df = pd.read_sql_query("SELECT * FROM iocs ORDER BY COALESCE(last_seen, first_seen) DESC", con)
con.close()

col1, col2 = st.columns(2)
with col1:
    artifact = st.text_input("Filtro por artifact (npm/pypi/cdn)")
with col2:
    ioc_type = st.multiselect("Tipo IOC", ["ip","domain","url","hash","email","c2","asn"])

if artifact:
    df = df[df["artifact"].fillna("").str.contains(artifact, case=False)]
if ioc_type:
    df = df[df["type"].isin(ioc_type)]

st.dataframe(df, use_container_width=True)
st.download_button("Descargar CSV", df.to_csv(index=False), "iocs.csv", "text/csv")
