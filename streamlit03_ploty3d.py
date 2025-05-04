import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import io
import xlsxwriter

st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# Carrega o CSV
file_path = "relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")

# Conversões de tipo
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
df["item_price"] = pd.to_numeric(df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["item_cost"] = pd.to_numeric(df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["totalValue"] = pd.to_numeric(df["totalValue"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")

# Filtros
st.sidebar.header("Filtros")
start_date = date(2025, 1, 1)
end_date = date.today()
selected_date = st.sidebar.date_input("Intervalo de datas:", [start_date, end_date])
if isinstance(selected_date, list) and len(selected_date) == 2:
    start_date, end_date = selected_date

df = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

produto = st.sidebar.selectbox("Produto", options=["Todos"] + sorted(df["item_title"].dropna().unique().tolist()))
canal = st.sidebar.selectbox("Canal", options=["Todos"] + sorted(df["channel"].dropna().unique().tolist()))
status = st.sidebar.selectbox("Status", options=["Todos"] + sorted(df["status"].dropna().unique().tolist()))
sku = st.sidebar.selectbox("SKU", options=["Todos"] + sorted(df["item_sku"].dropna().unique().tolist()))

if produto != "Todos":
    df = df[df["item_title"] == produto]
if canal != "Todos":
    df = df[df["channel"] == canal]
if status != "Todos":
    df = df[df["status"] == status]
if sku != "Todos":
    df = df[df["item_sku"] == sku]

# KPIs
vendas_total = df["totalValue"].sum()
quantidade_total = df["item_quantity"].sum()
ticket_medio = vendas_total / quantidade_total if quantidade_total else 0
lucro_total = (df["item_price"] - df["item_cost"]).sum()
margem_media = (lucro_total / vendas_total * 100) if vendas_total else 0

st.markdown("""
<style>
.kpi-box {
    border: 1px solid #CCC;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    background-color: #f9f9f9;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.05);
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div class='kpi-box'><h4>💰 Valor Total</h4><p style='font-size:22px;'>R$ {vendas_total:,.2f}</p></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-box'><h4>📦 Itens Vendidos</h4><p style='font-size:22px;'>{quantidade_total:,.0f}</p></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-box'><h4>🧾 Ticket Médio</h4><p style='font-size:22px;'>R$ {ticket_medio:,.2f}</p></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='kpi-box'><h4>📈 Margem Média</h4><p style='font-size:22px;'>{margem_media:.2f}%</p></div>", unsafe_allow_html=True)

# Gráficos
st.subheader("📆 Vendas por Dia")
diario = df.groupby(df["dateCreated"].dt.date)["totalValue"].sum().reset_index()
fig1 = px.line(diario, x="dateCreated", y="totalValue", title="Evolução Diária de Vendas")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("🏆 Top Produtos por Quantidade")
top_produtos = df.groupby("item_title")["item_quantity"].sum().nlargest(10).reset_index()
fig2 = px.pie(top_produtos, names="item_title", values="item_quantity", title="Top 10 Produtos")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("🌳 Lucro por Produto")
df["lucro_unitario"] = df["item_price"] - df["item_cost"]
lucro = df.groupby("item_title")["lucro_unitario"].sum().nlargest(10).reset_index()
fig3 = px.treemap(lucro, path=["item_title"], values="lucro_unitario", title="Top Lucro por Produto")
st.plotly_chart(fig3, use_container_width=True)

st.subheader("📊 Vendas por Mês")
df["mes"] = df["dateCreated"].dt.to_period("M").astype(str)
mensal = df.groupby("mes")["totalValue"].sum().reset_index()
fig4 = px.area(mensal, x="mes", y="totalValue", title="Vendas por Mês")
st.plotly_chart(fig4, use_container_width=True)

st.subheader("💲 Distribuição de Preços")
fig5 = px.violin(df, y="item_price", box=True, points="all", title="Distribuição de Preço")
st.plotly_chart(fig5, use_container_width=True)

st.subheader("🔎 Correlação Preço x Custo")
fig6 = px.scatter(df, x="item_price", y="item_cost", title="Preço vs Custo")
st.plotly_chart(fig6, use_container_width=True)

st.subheader("🔥 Mapa de Calor: Produto x Data")
fig7 = px.density_heatmap(df, x=df["dateCreated"].dt.date, y="item_title", nbinsx=30, title="Mapa de Calor de Vendas")
st.plotly_chart(fig7, use_container_width=True)

st.subheader("📦 Boxplot de Custos")
fig8 = px.box(df, x="item_title", y="item_cost", title="Boxplot de Custos")
st.plotly_chart(fig8, use_container_width=True)

# Exportação
st.subheader("📤 Exportar Dados")
df.drop(columns=["mes"], errors="ignore", inplace=True)
col_csv, col_excel = st.columns(2)

csv = df.to_csv(index=False, sep=";", encoding="utf-8")
col_csv.download_button("📄 Baixar CSV", data=csv, file_name="dados_filtrados.csv", mime="text/csv")

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    df.to_excel(writer, index=False, sheet_name='Vendas')
col_excel.download_button("📊 Baixar Excel", data=buffer.getvalue(), file_name="dados_filtrados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
