import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# 📥 Leitura do CSV
df = pd.read_csv("relatorio_magis5_97048_registros_2025-04-26_07-59-04.csv", sep=";", encoding="latin1")

# 🧹 Limpeza e conversões
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
df["item_price"] = pd.to_numeric(df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["item_cost"] = pd.to_numeric(df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["totalValue"] = pd.to_numeric(df["totalValue"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")

# 📅 Filtros de data
st.sidebar.header("📅 Filtros")
start_date = st.sidebar.date_input("Data inicial", df["dateCreated"].min().date())
end_date = st.sidebar.date_input("Data final", df["dateCreated"].max().date())
df_filtrado = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

# 1. 💰 Vendas por dia
st.subheader("💰 Total de Vendas por Dia")
vendas_por_dia = df_filtrado.groupby(df_filtrado["dateCreated"].dt.date)["totalValue"].sum().reset_index()
vendas_por_dia["totalValueFormatado"] = vendas_por_dia["totalValue"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))

fig1 = px.line(
    vendas_por_dia,
    x="dateCreated",
    y="totalValue",
    markers=True,
    labels={"dateCreated": "Data", "totalValue": "Total (R$)"},
    title="Evolução das Vendas"
)
fig1.update_traces(text=vendas_por_dia["totalValueFormatado"], hovertemplate="Data: %{x}<br>Total: %{text}<extra></extra>")
st.plotly_chart(fig1, use_container_width=True)

# 2. 📦 Itens mais vendidos
st.subheader("📦 Top 10 Itens mais Vendidos")
mais_vendidos = df_filtrado["item_title"].value_counts().head(10).reset_index()
mais_vendidos.columns = ["item_title", "quantidade"]

fig2 = px.bar(
    mais_vendidos,
    x="quantidade",
    y="item_title",
    orientation="h",
    text="quantidade",
    labels={"item_title": "Produto", "quantidade": "Quantidade"},
    title="Top 10 Produtos por Quantidade Vendida"
)

fig2.update_traces(textposition="outside")

st.plotly_chart(fig2, use_container_width=True)

# 3. 📈 Lucro por Produto (barras horizontais)
st.subheader("📈 Top 10 Produtos por Lucro Total")

df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = df_filtrado.groupby("item_title")[["lucro_unitario"]].sum().sort_values(by="lucro_unitario", ascending=False).head(10)
lucro = lucro.reset_index()
lucro["lucro_formatado"] = lucro["lucro_unitario"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))

fig4 = px.bar(
    lucro,
    x="lucro_unitario",
    y="item_title",
    orientation="h",
    text="lucro_formatado",
    labels={"item_title": "Produto", "lucro_unitario": "Lucro Total (R$)"},
    title="Top 10 Produtos por Lucro Total"
)

fig4.update_traces(textposition="outside")
fig4.update_layout(
    yaxis=dict(title="Produto"),
    xaxis=dict(title="Lucro Total (R$)"),
    margin=dict(l=0, r=0, t=50, b=0),
    height=600
)

st.plotly_chart(fig4, use_container_width=True)
