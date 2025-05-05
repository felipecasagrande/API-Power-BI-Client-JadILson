import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Dashboard Magis5", layout="wide", initial_sidebar_state="expanded")

# Tema escuro
tema_escuro = st.sidebar.toggle("🌗 Tema Escuro", value=True)
if not tema_escuro:
    st.markdown("<style>body { background-color: white; color: black; }</style>", unsafe_allow_html=True)

st.markdown("<div style='display: flex; align-items: center; gap: 10px;'>📦 <h1 style='display: inline;'>Dashboard Magis5 - Relatório de Vendas</h1><span style='font-size: 19.2px; color: #00d4ff; font-weight: bold;'>(Filtros)</span></div>", unsafe_allow_html=True)

# Leitura e tratamento
file_path = "relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")
df = df[["dateCreated", "item_title", "item_sku", "channel", "status", "item_quantity", "item_price", "item_cost", "totalValue"]]
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
for col in ["item_price", "item_cost", "totalValue"]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")

# Filtros
start_date = date(2025, 1, 1)
end_date = date.today()
selected_date = st.sidebar.date_input("Intervalo de datas:", [start_date, end_date])
if len(selected_date) == 2:
    start_date, end_date = selected_date
df = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

with st.sidebar.expander("Filtros Avançados", expanded=True):
    produtos = st.multiselect("Produto", sorted(df["item_title"].dropna().unique()))
    canais = st.multiselect("Canal", sorted(df["channel"].dropna().unique()))
    status_sel = st.multiselect("Status", sorted(df["status"].dropna().unique()))
    skus = st.multiselect("SKU", sorted(df["item_sku"].dropna().unique()))

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
    font-size: 19.2px;
    background-color: #003366;
    color: white;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
}
.kpi-container {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
}
.kpi-item {
    flex: 1;
    margin: 5px;
    min-width: 140px;
}
select, input, .stMultiSelect > div { font-size: 19.2px !important; }
text, .stText, .stLabel, .stDownloadButton, .stButton, .stTextInput > div > input, .stDateInput, .stSelectbox > div > div, .stDataFrame { font-size: 19.2px !important; }
h2 { font-size: 19.2px !important; }
</style>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-box kpi-item">💰<br>Valor Total<br><b>R$ {vendas_total:,.2f}</b></div>
    <div class="kpi-box kpi-item">📦<br>Itens Vendidos<br><b>{quantidade_total:,.0f}</b></div>
    <div class="kpi-box kpi-item">🧾<br>Ticket Médio<br><b>R$ {ticket_medio:,.2f}</b></div>
    <div class="kpi-box kpi-item">📈<br>Margem Média<br><b>{margem_media:.2f}%</b></div>
</div>
""", unsafe_allow_html=True)

# Agrupamentos
df["mes"] = df["dateCreated"].dt.to_period("M").astype(str)
df["canal_resumido"] = df["channel"].astype(str).str.split("-").str[0]

tabs = st.tabs(["📊 Gráficos 1", "📈 Gráficos 2", "📤 Exportar"])

with tabs[0]:
    st.subheader("📆 Total de Vendas por Dia")
    vendas_dia = df.groupby(df["dateCreated"].dt.date)["totalValue"].sum().reset_index()
    fig_dia = px.line(vendas_dia, x="dateCreated", y="totalValue", markers=True)
    st.plotly_chart(fig_dia, use_container_width=True)

    st.subheader("📊 Vendas por Mês")
    vendas_mes = df.groupby("mes")["totalValue"].sum().reset_index()
    fig_mes = px.bar(vendas_mes, x="mes", y="totalValue", text="totalValue")
    fig_mes.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    st.plotly_chart(fig_mes, use_container_width=True)

    st.subheader("📊 Quantidade de Vendas por Canal")
    quantidade_canal = df.groupby("canal_resumido")["item_quantity"].sum().reset_index().sort_values(by="item_quantity", ascending=False)
    fig_qtd = px.pie(quantidade_canal, names="canal_resumido", values="item_quantity", title="Distribuição de Quantidade por Canal")
    st.plotly_chart(fig_qtd, use_container_width=True)

with tabs[1]:
    st.subheader("📈 Gráfico Invertido: Total de Vendas por Canal e Mês")
    canal_mes = df.groupby(["canal_resumido", "mes"])["totalValue"].sum().reset_index()
    fig_inv = px.bar(
        canal_mes,
        x="canal_resumido", y="totalValue", color="mes",
        barmode="group",
        title="Total por Canal e Mês (Canal no Eixo X)"
    )
    fig_inv.update_layout(
        xaxis_tickangle=-90,
        xaxis_title="Canal",
        yaxis_title="Valor Total",
        legend_title="Mês",
        legend_orientation="h",
        legend_y=-0.3
    )
    st.plotly_chart(fig_inv, use_container_width=True)

    st.subheader("📈 Evolução do Ticket Médio por Canal (Invertido)")
    ticket_canal_mes = df.groupby(["mes", "canal_resumido"]).apply(lambda x: x["totalValue"].sum() / x["item_quantity"].sum()).reset_index(name="ticket_medio")
    ticket_canal_mes = ticket_canal_mes.sort_values(by="ticket_medio", ascending=False)
    fig_ticket = px.bar(ticket_canal_mes, x="ticket_medio", y="canal_resumido", color="mes", orientation="h")
    fig_ticket.update_layout(
        legend_orientation="h",
        legend_y=-0.3,
        yaxis_title="Canal",
        xaxis_title="Ticket Médio"
    )
    st.plotly_chart(fig_ticket, use_container_width=True)

with tabs[2]:
    st.subheader("📤 Exportar Dados Filtrados em CSV")
    csv = df.to_csv(index=False, sep=";", encoding="utf-8")
    st.download_button("📥 Baixar CSV", data=csv, file_name="dados_filtrados.csv", mime="text/csv")
