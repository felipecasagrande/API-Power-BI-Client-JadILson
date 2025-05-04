import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import io
import xlsxwriter

st.set_page_config(page_title="Dashboard Magis5", layout="wide")

# Alternância de tema
tema_escuro = st.sidebar.toggle("🌗 Tema Escuro", value=True)
if not tema_escuro:
    st.markdown("""<style>body { background-color: white; color: black; }</style>""", unsafe_allow_html=True)

st.title("📦 Dashboard Magis5 - Relatório de Vendas")

file_path = "relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")

# Conversão e limpeza
df = df[["dateCreated", "item_title", "item_sku", "channel", "status", "item_quantity", "item_price", "item_cost", "totalValue"]]
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
df["item_price"] = pd.to_numeric(df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["item_cost"] = pd.to_numeric(df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["totalValue"] = pd.to_numeric(df["totalValue"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")

# Filtros
st.sidebar.header("Filtros")
start_date = date(2025, 1, 1)
end_date = date.today()
selected_date = st.sidebar.date_input("Intervalo de datas:", [start_date, end_date])
if len(selected_date) == 2:
    start_date, end_date = selected_date

df = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

with st.sidebar.expander("Filtros Avançados", expanded=True):
    produtos = st.multiselect("Produto", options=sorted(df["item_title"].dropna().unique().tolist()))
    canais = st.multiselect("Canal", options=sorted(df["channel"].dropna().unique().tolist()))
    status_sel = st.multiselect("Status", options=sorted(df["status"].dropna().unique().tolist()))
    skus = st.multiselect("SKU", options=sorted(df["item_sku"].dropna().unique().tolist()))

if produtos:
    df = df[df["item_title"].isin(produtos)]
if canais:
    df = df[df["channel"].isin(canais)]
if status_sel:
    df = df[df["status"].isin(status_sel)]
if skus:
    df = df[df["item_sku"].isin(skus)]

# KPIs
vendas_total = df["totalValue"].sum()
quantidade_total = df["item_quantity"].sum()
ticket_medio = vendas_total / quantidade_total if quantidade_total else 0
lucro_total = (df["item_price"] - df["item_cost"]).sum()
margem_media = (lucro_total / vendas_total * 100) if vendas_total else 0

st.markdown("""
<style>
.kpi-box {
    background-color: #003366;
    color: white;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    font-size: 18px;
}
.kpi-icon {
    font-size: 22px;
    display: block;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div class='kpi-box'><div class='kpi-icon'>💰</div><div>Valor Total<br>R$ {vendas_total:,.2f}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-box'><div class='kpi-icon'>📦</div><div>Itens Vendidos<br>{quantidade_total:,.0f}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-box'><div class='kpi-icon'>🧾</div><div>Ticket Médio<br>R$ {ticket_medio:,.2f}</div></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='kpi-box'><div class='kpi-icon'>📈</div><div>Margem Média<br>{margem_media:.2f}%</div></div>", unsafe_allow_html=True)

# Abas
abas = st.tabs(["📆 Vendas por Dia", "📊 Vendas por Mês", "🧮 Ticket por Canal", "🏆 Top Produtos", "🌳 Lucro por Produto", "💲 Preços", "📦 Custos", "📤 Exportar"])

with abas[0]:
    st.subheader("📆 Vendas por Dia")
    vendas_dia = df.groupby(df["dateCreated"].dt.date)["totalValue"].sum().reset_index()
    fig = px.line(vendas_dia, x="dateCreated", y="totalValue", markers=True, title="Total de Vendas por Dia")
    st.plotly_chart(fig, use_container_width=True)

with abas[1]:
    st.subheader("📊 Vendas por Mês")
    df["mes"] = df["dateCreated"].dt.to_period("M").astype(str)
    vendas_mes = df.groupby("mes")["totalValue"].sum().reset_index()
    fig = px.bar(vendas_mes, x="mes", y="totalValue", title="Total de Vendas por Mês")
    st.plotly_chart(fig, use_container_width=True)

with abas[2]:
    st.subheader("🧮 Ticket Médio por Canal")
    ticket_canal = df.groupby("channel").apply(lambda x: x["totalValue"].sum() / x["item_quantity"].sum()).reset_index(name="ticket_medio")
    fig = px.bar(ticket_canal, x="channel", y="ticket_medio", title="Ticket Médio por Canal")
    st.plotly_chart(fig, use_container_width=True)

with abas[3]:
    st.subheader("🏆 Top Produtos por Quantidade")
    top_prod = df["item_title"].value_counts().head(10).reset_index()
    top_prod.columns = ["Produto", "Quantidade"]
    fig = px.pie(top_prod, values="Quantidade", names="Produto", title="Top 10 Produtos")
    st.plotly_chart(fig, use_container_width=True)

with abas[4]:
    st.subheader("🌳 Lucro por Produto")
    df["lucro_unitario"] = df["item_price"] - df["item_cost"]
    lucro = df.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10).reset_index()
    fig = px.treemap(lucro, path=["item_title"], values="lucro_unitario", title="Lucro Total por Produto")
    st.plotly_chart(fig, use_container_width=True)

with abas[5]:
    st.subheader("💲 Top 10 Preços por Produto")
    top_precos = df.groupby("item_title")["item_price"].mean().sort_values(ascending=False).head(10).reset_index()
    fig = px.bar(top_precos, x="item_price", y="item_title", orientation="h", title="Top 10 Preços")
    st.plotly_chart(fig, use_container_width=True)

with abas[6]:
    st.subheader("📦 Top 10 Custos por Produto")
    top_custos = df.groupby("item_title")["item_cost"].mean().sort_values(ascending=False).head(10).reset_index()
    fig = px.bar(top_custos, x="item_cost", y="item_title", orientation="h", title="Top 10 Custos")
    st.plotly_chart(fig, use_container_width=True)

with abas[7]:
    st.subheader("📤 Exportar Dados Filtrados")
    df_export = df.copy()
    for col in df_export.columns:
        if df_export[col].dtype == "object":
            df_export[col] = df_export[col].astype(str).str.slice(0, 32767)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Vendas')

    st.download_button(
        label="📥 Baixar Excel",
        data=buffer.getvalue(),
        file_name="vendas_filtradas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
