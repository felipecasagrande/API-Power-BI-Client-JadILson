import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import io
import xlsxwriter

st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

file_path = "relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")

# Conversão e limpeza
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
aba = st.tabs(["📆 Vendas por Dia", "🏆 Top Produtos", "🌳 Lucro", "📊 Vendas por Mês", "💲 Preços", "📦 Custos", "📤 Exportar"])

with aba[0]:
    diario = df.groupby(df["dateCreated"].dt.date)["totalValue"].sum().reset_index()
    fig = px.line(diario, x="dateCreated", y="totalValue", title="Vendas Diárias")
    st.plotly_chart(fig, use_container_width=True)

with aba[1]:
    top_prod = df.groupby("item_title")["item_quantity"].sum().nlargest(10).reset_index()
    fig = px.pie(top_prod, names="item_title", values="item_quantity", title="Top Produtos por Quantidade")
    st.plotly_chart(fig, use_container_width=True)

with aba[2]:
    df["lucro_unitario"] = df["item_price"] - df["item_cost"]
    lucro = df.groupby("item_title")["lucro_unitario"].sum().nlargest(10).reset_index()
    fig = px.treemap(lucro, path=["item_title"], values="lucro_unitario", title="Lucro por Produto")
    fig.update_traces(textfont=dict(size=28))
    st.plotly_chart(fig, use_container_width=True)

with aba[3]:
    df["mes"] = df["dateCreated"].dt.to_period("M").astype(str)
    mensal = df.groupby("mes")["totalValue"].sum().reset_index()
    fig = px.area(mensal, x="mes", y="totalValue", title="Vendas por Mês", text="totalValue")
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

with aba[4]:
    top_price = df.nlargest(50, "item_price")
    fig = px.scatter(top_price, x="item_title", y="item_price", title="Top 50 Preços")
    fig.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

with aba[5]:
    top_custo = df.nlargest(50, "item_cost")
    fig = px.box(top_custo, x="item_title", y="item_cost", title="Top 50 Custos")
    fig.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

with aba[6]:
    st.subheader("Exportar Dados")
    df.drop(columns=["mes"], errors="ignore", inplace=True)
    col_csv, col_excel = st.columns(2)

    csv = df.to_csv(index=False, sep=";", encoding="utf-8")
    col_csv.download_button("📄 Baixar CSV", data=csv, file_name="dados_filtrados.csv", mime="text/csv")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        try:
            df.to_excel(writer, index=False, sheet_name='Vendas')
        except ValueError:
            df.astype(str).to_excel(writer, index=False, sheet_name='Vendas')
    col_excel.download_button("📊 Baixar Excel", data=buffer.getvalue(), file_name="dados_filtrados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
