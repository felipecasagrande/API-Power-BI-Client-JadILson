import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import io
import xlsxwriter

# Configuração da página
st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# 📥 Leitura do CSV
file_path = "relatorio_magis5_98900_registros_2025-05-04_07-46-08.csv"
df = pd.read_csv(file_path, sep=";", encoding="latin1")

# 🧹 Limpeza e conversões
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")
df["item_price"] = pd.to_numeric(df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["item_cost"] = pd.to_numeric(df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")
df["totalValue"] = pd.to_numeric(df["totalValue"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True), errors="coerce")


# 🎛 Filtros na Sidebar
st.sidebar.header("📅 Filtros de Data")
start_date = st.sidebar.date_input("Data inicial", df["dateCreated"].min().date())
end_date = st.sidebar.date_input("Data final", df["dateCreated"].max().date())

produtos_disponiveis = df["item_title"].dropna().unique() if "item_title" in df.columns else []
produto_selecionado = st.sidebar.selectbox("Produto", options=["Todos"] + list(produtos_disponiveis))

# 🎯 Novos Filtros
canais_disponiveis = df["salesChannel"].dropna().unique() if "salesChannel" in df.columns else []
canal_selecionado = st.sidebar.selectbox("Canal de Venda", options=["Todos"] + list(canais_disponiveis))

status_disponiveis = df["status"].dropna().unique() if "status" in df.columns else []
status_selecionado = st.sidebar.selectbox("Status", options=["Todos"] + list(status_disponiveis))

skus_disponiveis = df["sku"].dropna().unique() if "sku" in df.columns else []
sku_selecionado = st.sidebar.selectbox("SKU", options=["Todos"] + list(skus_disponiveis))
 # Aplicação dos filtros
 df_filtrado = df[
     (df["dateCreated"].dt.date >= start_date) &
     (df["dateCreated"].dt.date <= end_date)
 ]
 if produto_selecionado != "Todos":
     df_filtrado = df_filtrado[df_filtrado["item_title"] == produto_selecionado]
 if canal_selecionado != "Todos" and "salesChannel" in df.columns:
     df_filtrado = df_filtrado[df_filtrado["salesChannel"] == canal_selecionado]
 if status_selecionado != "Todos" and "status" in df.columns:
     df_filtrado = df_filtrado[df_filtrado["status"] == status_selecionado]
 if sku_selecionado != "Todos" and "sku" in df.columns:
     df_filtrado = df_filtrado[df_filtrado["sku"] == sku_selecionado]
# KPIs
vendas_total = df_filtrado["totalValue"].sum()
quantidade_total = df_filtrado["item_title"].count()

col1, col2 = st.columns(2)
col1.metric("💵 Valor Total de Vendas", f"R$ {vendas_total:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
col2.metric("📦 Quantidade de Itens Vendidos", f"{quantidade_total:,}".replace(",", "."))

# 📊 Evolução das Vendas
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

# 📦 Top Itens por Quantidade
st.subheader("📦 Top 10 Itens mais Vendidos")
mais_vendidos = df_filtrado["item_title"].value_counts().head(10).reset_index()
mais_vendidos.columns = ["item_title", "quantidade"]

fig2 = px.pie(
    mais_vendidos,
    values="quantidade",
    names="item_title",
    title="Participação dos 10 Itens mais Vendidos"
)
st.plotly_chart(fig2, use_container_width=True)

# 📈 Top Produtos por Lucro
st.subheader("📈 Top 10 Produtos por Lucro Total")
df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = df_filtrado.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10).reset_index()
lucro["lucro_formatado"] = lucro["lucro_unitario"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))

fig3 = px.treemap(
    lucro,
    path=["item_title"],
    values="lucro_unitario",
    title="Lucro Total por Produto (Top 10)",
)
st.plotly_chart(fig3, use_container_width=True)

# 🔄 Vendas por canal
if "salesChannel" in df.columns:
    st.subheader("🛍️ Vendas por Canal de Venda")
    vendas_por_canal = df_filtrado["salesChannel"].value_counts().reset_index()
    vendas_por_canal.columns = ["Canal", "Quantidade"]
    fig4 = px.funnel(
        vendas_por_canal,
        x="Quantidade",
        y="Canal",
        title="Distribuição das Vendas por Canal"
    )
    st.plotly_chart(fig4, use_container_width=True)

# 📅 Evolução mensal
st.subheader("📅 Evolução Mensal de Vendas")
df_filtrado["mes"] = df_filtrado["dateCreated"].dt.to_period("M").astype(str)
mensal = df_filtrado.groupby("mes")["totalValue"].sum().reset_index()
fig5 = px.area(
    mensal,
    x="mes",
    y="totalValue",
    title="Vendas Totais por Mês",
    labels={"mes": "Mês", "totalValue": "Total Vendido (R$)"}
)
st.plotly_chart(fig5, use_container_width=True)

# 📊 Novos Gráficos adicionais
st.subheader("🧭 Distribuição de Preço dos Produtos")
fig6 = px.violin(df_filtrado, y="item_price", box=True, points="all", title="Distribuição de Preço dos Produtos")
st.plotly_chart(fig6, use_container_width=True)

st.subheader("🔍 Correlação entre Preço e Custo")
fig7 = px.scatter(df_filtrado, x="item_price", y="item_cost", title="Correlação entre Preço e Custo", trendline="ols")
st.plotly_chart(fig7, use_container_width=True)

st.subheader("📌 Densidade de Vendas por Data")
fig8 = px.density_heatmap(df_filtrado, x=df_filtrado["dateCreated"].dt.date, y="item_title", nbinsx=30, title="Mapa de Calor de Vendas por Produto e Data")
st.plotly_chart(fig8, use_container_width=True)

st.subheader("📦 Boxplot de Custo dos Produtos")
fig9 = px.box(df_filtrado, x="item_title", y="item_cost", title="Boxplot de Custos por Produto")
st.plotly_chart(fig9, use_container_width=True)

# 📤 Exportação
df_filtrado.drop(columns=["mes"], errors="ignore", inplace=True)
st.subheader("📤 Exportar Dados Filtrados")
col_csv, col_excel = st.columns(2)

csv = df_filtrado.to_csv(index=False, sep=";", encoding="utf-8")
col_csv.download_button(
    label="📄 Baixar CSV",
    data=csv,
    file_name="dados_filtrados.csv",
    mime="text/csv"
)

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    df_filtrado.to_excel(writer, index=False, sheet_name='Vendas')

col_excel.download_button(
    label="📊 Baixar Excel",
    data=buffer.getvalue(),
    file_name="dados_filtrados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
