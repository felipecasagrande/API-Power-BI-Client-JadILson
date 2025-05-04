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
aba = st.tabs(["📆 Vendas por Dia", "🧮 Ticket por Canal", "🏆 Top Produtos", "🌳 Lucro", "📊 Vendas por Mês", "📈 Comparativo Canais", "💲 Preços", "📦 Custos", "📤 Exportar"])

with aba[0]:
    st.subheader("📅 Vendas por Dia")
    vendas_dia = df.groupby(df["dateCreated"].dt.date)["totalValue"].sum().reset_index()
    fig = px.line(vendas_dia, x="dateCreated", y="totalValue", title="Vendas por Dia")
    fig.update_traces(mode="lines+markers", hovertemplate="Data: %{x}<br>Total: R$ %{y:,.2f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

with aba[1]:
    st.subheader("🧮 Ticket Médio por Canal")
    if "channel" in df.columns:
        ticket_canal = df.groupby("channel").apply(lambda x: x["totalValue"].sum() / x["item_quantity"].sum()).reset_index(name="ticket")
        fig = px.bar(ticket_canal, x="channel", y="ticket", title="Ticket Médio por Canal", labels={"ticket": "R$ Ticket Médio"})
        fig.update_traces(hovertemplate='Canal: %{x}<br>Ticket Médio: R$ %{y:,.2f}<extra></extra>')
        st.plotly_chart(fig, use_container_width=True)

with aba[2]:
    st.subheader("🏆 Top Produtos")
    top_prod = df["item_title"].value_counts().head(10).reset_index()
    top_prod.columns = ["Produto", "Quantidade"]
    fig = px.pie(top_prod, names="Produto", values="Quantidade", title="Top 10 Produtos Mais Vendidos")
    st.plotly_chart(fig, use_container_width=True)

with aba[3]:
    st.subheader("🌳 Lucro por Produto")
    df["lucro"] = df["item_price"] - df["item_cost"]
    lucro_prod = df.groupby("item_title")["lucro"].sum().sort_values(ascending=False).head(10).reset_index()
    fig = px.treemap(lucro_prod, path=["item_title"], values="lucro", title="Lucro por Produto")
    st.plotly_chart(fig, use_container_width=True)

with aba[4]:
    df["mes"] = df["dateCreated"].dt.to_period("M").astype(str)
    mensal = df.groupby("mes")["totalValue"].sum().reset_index()
    mensal["variacao"] = mensal["totalValue"].pct_change().fillna(0) * 100
    st.subheader("📊 Tabela de Vendas Mensais")
    st.dataframe(mensal.rename(columns={"totalValue": "Vendas", "variacao": "% Variação"}).style.format({"Vendas": "R$ {:,.2f}", "% Variação": "{:.2f}%"}))
    fig = px.area(mensal, x="mes", y="totalValue", title="Vendas por Mês", text=mensal["totalValue"].map(lambda x: f"R$ {x:,.0f}"))
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

with aba[5]:
    st.subheader("📈 Comparativo de Vendas entre Canais")
    if "channel" in df.columns:
        comparativo = df.groupby(["channel", df["dateCreated"].dt.to_period("M").astype(str)]) ["totalValue"].sum().reset_index()
        fig = px.line(comparativo, x="dateCreated", y="totalValue", color="channel", markers=True, title="Vendas por Canal ao Longo dos Meses")
        fig.update_traces(hovertemplate='Canal: %{legendgroup}<br>Mês: %{x}<br>Total: R$ %{y:,.2f}<extra></extra>')
        st.plotly_chart(fig, use_container_width=True)

with aba[6]:
    st.subheader("Top 50 Preços")
    top_preco = df.groupby("item_title")["item_price"].sum().sort_values(ascending=False).head(50).reset_index()
    fig = px.bar(top_preco, x="item_price", y="item_title", orientation="h", title="Top 50 Preços por Produto", labels={"item_price": "Preço Total", "item_title": "Produto"})
    fig.update_layout(xaxis_tickprefix="R$ ")
    st.plotly_chart(fig, use_container_width=True)

with aba[7]:
    st.subheader("Top 50 Custos")
    top_custo = df.groupby("item_title")["item_cost"].sum().sort_values(ascending=False).head(50).reset_index()
    fig = px.bar(top_custo, x="item_cost", y="item_title", orientation="h", title="Top 50 Custos por Produto", labels={"item_cost": "Custo Total", "item_title": "Produto"})
    fig.update_layout(xaxis_tickprefix="R$ ")
    st.plotly_chart(fig, use_container_width=True)

with aba[8]:
    st.subheader("📤 Exportar Dados Filtrados")
    csv = df.to_csv(index=False, sep=";", encoding="utf-8")
    st.download_button("📄 Baixar CSV", data=csv, file_name="dados_filtrados.csv", mime="text/csv")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendas')
    st.download_button("📊 Baixar Excel", data=buffer.getvalue(), file_name="dados_filtrados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
