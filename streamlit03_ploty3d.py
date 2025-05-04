import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import io
import xlsxwriter

# Configuração da página
st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# 📥 Leitura do CSV fixo
file_path = "streamlit/relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")

# 🧹 Limpeza e conversões
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
df["item_price"] = pd.to_numeric(df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["item_cost"] = pd.to_numeric(df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["totalValue"] = pd.to_numeric(df["totalValue"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")

# 🎛 Filtros na Sidebar
st.sidebar.header("📅 Filtros de Data")
start_date = date(2025, 1, 1)
end_date = date.today()
selected_date = st.sidebar.date_input("Intervalo de datas:", [start_date, end_date])
if isinstance(selected_date, list) and len(selected_date) == 2:
    start_date, end_date = selected_date

produtos_disponiveis = df["item_title"].dropna().unique()
produto_selecionado = st.sidebar.selectbox("Produto", options=["Todos"] + list(produtos_disponiveis))

# Aplicação dos filtros
df_filtrado = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

if produto_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["item_title"] == produto_selecionado]

# 📊 KPIs com borda e novos indicadores
vendas_total = df_filtrado["totalValue"].sum()
quantidade_total = df_filtrado["item_title"].count()
ticket_medio = vendas_total / quantidade_total if quantidade_total > 0 else 0
lucro_total = (df_filtrado["item_price"] - df_filtrado["item_cost"]).sum()
margem_media = (lucro_total / vendas_total * 100) if vendas_total > 0 else 0

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
    st.markdown(f"<div class='kpi-box'><h4>💵 Valor Total</h4><p style='font-size:22px;'>R$ {vendas_total:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".") + "</p></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-box'><h4>📦 Itens Vendidos</h4><p style='font-size:22px;'>{quantidade_total:,}".replace(",", ".") + "</p></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-box'><h4>🧮 Ticket Médio</h4><p style='font-size:22px;'>R$ {ticket_medio:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".") + "</p></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='kpi-box'><h4>📊 Margem Média</h4><p style='font-size:22px;'>{margem_media:.1f}%</p></div>", unsafe_allow_html=True)

# 📈 Gráficos
st.subheader("💰 Vendas por Dia")
vendas_por_dia = df_filtrado.groupby(df_filtrado["dateCreated"].dt.date)["totalValue"].sum().reset_index()
fig1 = px.line(vendas_por_dia, x="dateCreated", y="totalValue", markers=True,
               labels={"dateCreated": "Data", "totalValue": "Total (R$)"},
               title="Evolução de Vendas Diária")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("📦 Top 10 Produtos por Quantidade")
mais_vendidos = df_filtrado["item_title"].value_counts().head(10).reset_index()
mais_vendidos.columns = ["item_title", "quantidade"]
fig2 = px.pie(mais_vendidos, values="quantidade", names="item_title", title="Top 10 Itens")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("📈 Top Produtos por Lucro Total")
df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = df_filtrado.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10).reset_index()
fig3 = px.treemap(lucro, path=["item_title"], values="lucro_unitario", title="Lucro Total por Produto")
st.plotly_chart(fig3, use_container_width=True)

st.subheader("📊 Evolução Mensal")
df_filtrado["mes"] = df_filtrado["dateCreated"].dt.to_period("M").astype(str)
mensal = df_filtrado.groupby("mes")["totalValue"].sum().reset_index()
fig4 = px.area(mensal, x="mes", y="totalValue", title="Vendas por Mês")
st.plotly_chart(fig4, use_container_width=True)

st.subheader("🧭 Distribuição de Preço")
fig5 = px.violin(df_filtrado, y="item_price", box=True, points="all")
st.plotly_chart(fig5, use_container_width=True)

st.subheader("🔍 Correlação Preço x Custo")
fig6 = px.scatter(df_filtrado, x="item_price", y="item_cost", title="Preço vs Custo")  # sem trendline
st.plotly_chart(fig6, use_container_width=True)

st.subheader("📌 Mapa de Calor de Vendas por Produto/Data")
fig7 = px.density_heatmap(df_filtrado, x=df_filtrado["dateCreated"].dt.date, y="item_title", nbinsx=30)
st.plotly_chart(fig7, use_container_width=True)

st.subheader("📦 Boxplot de Custos por Produto")
fig8 = px.box(df_filtrado, x="item_title", y="item_cost", title="Custos por Produto")
st.plotly_chart(fig8, use_container_width=True)

# 📤 Exportação
st.subheader("📤 Exportar Dados Filtrados")
df_filtrado.drop(columns=["mes"], errors="ignore", inplace=True)
col_csv, col_excel = st.columns(2)

csv = df_filtrado.to_csv(index=False, sep=";", encoding="utf-8")
col_csv.download_button("📄 Baixar CSV", data=csv, file_name="dados_filtrados.csv", mime="text/csv")

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    df_filtrado.to_excel(writer, index=False, sheet_name='Vendas')
col_excel.download_button("📊 Baixar Excel", data=buffer.getvalue(),
                          file_name="dados_filtrados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
