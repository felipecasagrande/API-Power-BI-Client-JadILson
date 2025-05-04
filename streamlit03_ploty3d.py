import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

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

# 📅 Filtros na barra lateral
st.sidebar.header("📅 Filtros")
start_date = st.sidebar.date_input("Data inicial", date(2025, 1, 1))
end_date = st.sidebar.date_input("Data final", date.today())

# Filtros adicionais
produtos = df["item_title"].dropna().unique()
produto_selecionado = st.sidebar.multiselect("Filtrar Produto(s)", produtos, default=produtos)

canais = df["salesChannel"].dropna().unique()
canal_selecionado = st.sidebar.multiselect("Filtrar Canal de Venda", canais, default=canais)

status = df["status"].dropna().unique()
status_selecionado = st.sidebar.multiselect("Filtrar Status do Pedido", status, default=status)

# Aplicação dos filtros
df_filtrado = df[
    (df["dateCreated"].dt.date >= start_date) &
    (df["dateCreated"].dt.date <= end_date) &
    (df["item_title"].isin(produto_selecionado)) &
    (df["salesChannel"].isin(canal_selecionado)) &
    (df["status"].isin(status_selecionado))
]

# KPIs Principais
vendas_total = df_filtrado["totalValue"].sum()
quantidade_total = df_filtrado["item_title"].count()

col1, col2 = st.columns(2)
col1.metric("💵 Valor Total de Vendas", f"R$ {vendas_total:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
col2.metric("📦 Quantidade de Itens Vendidos", f"{quantidade_total:,}".replace(",", "."))

# Gráfico de Vendas por Dia
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

# Itens mais vendidos
st.subheader("📦 Top 10 Itens mais Vendidos")
mais_vendidos = df_filtrado["item_title"].value_counts().head(10).reset_index()
mais_vendidos.columns = ["item_title", "quantidade"]

fig2 = px.bar(
    mais_vendidos,
    x="quantidade",
    y="item_title",
    orientation="h",
    labels={"item_title": "Produto", "quantidade": "Quantidade"},
    title="Top 10 Produtos por Quantidade Vendida",
    text="quantidade"
)
fig2.update_traces(textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

# Lucro por Produto
st.subheader("📈 Top 10 Produtos por Lucro Total")
df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = df_filtrado.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10).reset_index()
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
