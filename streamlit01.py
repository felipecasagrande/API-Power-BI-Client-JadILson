import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard Magis5", layout="wide")

# Carrega os dados
df = pd.read_csv("relatorio_magis5_97048_registros_2025-04-26_07-59-04.csv", sep=";")

df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")

st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# Filtros
st.sidebar.header("📅 Filtros")
start_date = st.sidebar.date_input("Data inicial", df["dateCreated"].min().date())
end_date = st.sidebar.date_input("Data final", df["dateCreated"].max().date())

df_filtrado = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

# 1. Vendas por dia
st.subheader("💰 Total de Vendas por Dia")
vendas_por_dia = df_filtrado.groupby(df_filtrado["dateCreated"].dt.date)["totalValue"].sum()
st.line_chart(vendas_por_dia)

# 2. Tipos de pagamento
st.subheader("💳 Tipos de Pagamento (em ordem decrescente)")
pagamento_ordenado = df_filtrado["payment_type"].value_counts().sort_values(ascending=False)
st.bar_chart(pagamento_ordenado)

# 3. Produtos mais vendidos
st.subheader("🔥 Top 10 Produtos Mais Vendidos")
produtos_vendidos = df_filtrado.groupby("item_title")["item_quantity"].sum().sort_values(ascending=False).head(10)
st.bar_chart(produtos_vendidos)

# 4. Status dos pedidos
st.subheader("📦 Quantidade de Pedidos por Status")
status_ordenado = df_filtrado["status"].value_counts().sort_values(ascending=False)
st.bar_chart(status_ordenado)

# 5. Pedidos por estado (UF)
if "shipping_state" in df_filtrado.columns:
    st.subheader("🗺️ Pedidos por Estado (UF)")
    pedidos_estado = df_filtrado["shipping_state"].value_counts().sort_values(ascending=False)
    st.bar_chart(pedidos_estado)

# 6. Lucro por produto (Top 10)
df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro_produto = df_filtrado.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10)

st.subheader("📈 Top 10 Produtos por Lucro Total")
st.bar_chart(lucro_produto)

# Dados brutos
if st.checkbox("📄 Mostrar dados brutos"):
    st.write(df_filtrado)
