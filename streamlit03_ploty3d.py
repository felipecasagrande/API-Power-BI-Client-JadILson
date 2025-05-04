import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Dashboard Magis5", layout="wide")

# Tema escuro/claro
tema_escuro = st.sidebar.toggle("🌗 Tema Escuro", value=True)
if not tema_escuro:
    st.markdown("<style>body { background-color: white; color: black; }</style>", unsafe_allow_html=True)

st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# Leitura dos dados
file_path = "relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")
df = df[["dateCreated", "item_title", "item_sku", "channel", "status", "item_quantity", "item_price", "item_cost", "totalValue"]]

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
    produtos = st.multiselect("Produto", sorted(df["item_title"].dropna().unique().tolist()))
    canais = st.multiselect("Canal", sorted(df["channel"].dropna().unique().tolist()))
    status_sel = st.multiselect("Status", sorted(df["status"].dropna().unique().tolist()))
    skus = st.multiselect("SKU", sorted(df["item_sku"].dropna().unique().tolist()))

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

# Abas separadas por dashboard
tabs = st.tabs([
    "📆 Vendas por Dia",
    "📊 Vendas por Mês",
    "📈 Variação por Canal",
    "📊 Ticket Médio por Canal",
    "📦 SKUs por Mês",
    "🔍 Segmentação Dinâmica",
    "📤 Exportar CSV"
])

with tabs[0]:
    st.subheader("📆 Total de Vendas por Dia")
    vendas_dia = df.groupby(df["dateCreated"].dt.date)["totalValue"].sum().reset_index()
    fig = px.line(vendas_dia, x="dateCreated", y="totalValue", markers=True, title="Total de Vendas por Dia")
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("📊 Vendas por Mês")
    df["mes"] = df["dateCreated"].dt.to_period("M").astype(str)
    vendas_mes = df.groupby("mes")["totalValue"].sum().reset_index()
    vendas_mes["variação"] = vendas_mes["totalValue"].pct_change() * 100
    fig = px.bar(vendas_mes, x="mes", y="totalValue", text="totalValue", title="Total de Vendas por Mês")
    fig.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("📈 Variação de Vendas por Canal")
    canal_mes = df.groupby(["mes", "channel"]).agg({"totalValue": "sum"}).reset_index()
    canal_mes["variação"] = canal_mes.groupby("channel")["totalValue"].pct_change() * 100
    fig_canal = px.line(canal_mes, x="mes", y="totalValue", color="channel", markers=True, title="Comparativo de Vendas por Canal")
    st.plotly_chart(fig_canal, use_container_width=True)

with tabs[3]:
    st.subheader("📈 Evolução do Ticket Médio por Canal")
    ticket_canal_mes = df.groupby(["mes", "channel"]).apply(lambda x: x["totalValue"].sum() / x["item_quantity"].sum()).reset_index(name="ticket_medio")
    fig_ticket = px.line(ticket_canal_mes, x="mes", y="ticket_medio", color="channel", markers=True, title="Ticket Médio por Canal por Mês")
    st.plotly_chart(fig_ticket, use_container_width=True)

with tabs[4]:
    st.subheader("📦 Comparativo de SKUs por Mês")
    sku_mes = df.groupby(["mes", "item_sku"])["totalValue"].sum().reset_index()
    top_skus = sku_mes.groupby("item_sku")["totalValue"].sum().nlargest(5).index.tolist()
    sku_mes = sku_mes[sku_mes["item_sku"].isin(top_skus)]
    fig_sku = px.bar(sku_mes, x="mes", y="totalValue", color="item_sku", barmode="group", title="Top 5 SKUs com maior faturamento")
    st.plotly_chart(fig_sku, use_container_width=True)

with tabs[5]:
    st.subheader("🔍 Segmentações por Coluna (Filtro Dinâmico)")
    col_selecionada = st.selectbox("Selecione uma coluna para agrupar:", options=df.columns)
    col_metric = st.selectbox("Selecione a métrica:", ["totalValue", "item_quantity", "item_price", "item_cost"])
    agrupado = df.groupby(col_selecionada)[col_metric].sum().reset_index().sort_values(by=col_metric, ascending=False).head(20)
    fig_dinamico = px.bar(agrupado, x=col_metric, y=col_selecionada, orientation="h", title=f"Top 20 por {col_selecionada} usando {col_metric}")
    st.plotly_chart(fig_dinamico, use_container_width=True)

with tabs[6]:
    st.subheader("📤 Exportar Dados Filtrados em CSV")
    csv = df.to_csv(index=False, sep=";", encoding="utf-8")
    st.download_button(
        label="📥 Baixar CSV",
        data=csv,
        file_name="dados_filtrados.csv",
        mime="text/csv"
    )
