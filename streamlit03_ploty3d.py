import streamlit as st
import pandas as pd
import plotly.express as px

# Configurações iniciais da página
st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# Leitura do arquivo CSV
df = pd.read_csv("relatorio_magis5_97048_registros_2025-04-26_07-59-04.csv", sep=";", encoding="latin1")

# Conversões e limpeza de dados
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
df["item_price"] = pd.to_numeric(df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["item_cost"] = pd.to_numeric(df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")

# Filtros de data
st.sidebar.header("📅 Filtros")
start_date = st.sidebar.date_input("Data inicial", df["dateCreated"].min().date())
end_date = st.sidebar.date_input("Data final", df["dateCreated"].max().date())
df_filtrado = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

# Tipos de pagamento
pagamento = df_filtrado["payment_type"].value_counts().reset_index()
pagamento.columns = ["Tipo de Pagamento", "Quantidade"]
fig1 = px.bar(pagamento, x="Tipo de Pagamento", y="Quantidade", title="💳 Tipos de Pagamento")
fig1.update_layout(xaxis_tickangle=90)
st.plotly_chart(fig1, use_container_width=True)

# Top 10 produtos mais vendidos
produtos = df_filtrado.groupby("item_title")["item_quantity"].sum().sort_values(ascending=False).head(10).reset_index()
fig2 = px.bar(produtos, x="item_quantity", y="item_title", orientation='h', title="🔥 Top 10 Produtos Mais Vendidos")
st.plotly_chart(fig2, use_container_width=True)

# Status dos pedidos
status = df_filtrado["status"].value_counts().reset_index()
status.columns = ["Status", "Quantidade"]
fig3 = px.bar(status, x="Status", y="Quantidade", title="📦 Status dos Pedidos")
fig3.update_layout(xaxis_tickangle=90)
st.plotly_chart(fig3, use_container_width=True)

# Lucro por produto
df_filtrado.loc[:, "lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = (
    df_filtrado.groupby("item_title")[["lucro_unitario"]]
    .sum()
    .sort_values(by="lucro_unitario", ascending=False)
    .head(10)
    .reset_index()
)
fig4 = px.bar(lucro, x="lucro_unitario", y="item_title", orientation='h', title="📈 Top 10 Produtos por Lucro Total")
st.plotly_chart(fig4, use_container_width=True)

# Mostrar dados brutos
if st.checkbox("📄 Mostrar dados brutos"):
    st.dataframe(df_filtrado)
