import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")

# 🔽 Leitura direta do arquivo na nuvem/local
df = pd.read_csv("relatorio_magis5_97048_registros_2025-04-26_07-59-04.csv", sep=";", encoding="latin1")

# 🔁 Conversões e limpeza de dados
df["dateCreated"] = pd.to_datetime(df["dateCreated"], errors="coerce")

# Converte colunas monetárias
df["item_price"] = pd.to_numeric(
    df["item_price"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True),
    errors="coerce"
)

df["item_cost"] = pd.to_numeric(
    df["item_cost"].astype(str).str.replace(",", ".").str.replace(r"[^\d\.]", "", regex=True),
    errors="coerce"
)

# 📅 Filtros de data
st.sidebar.header("📅 Filtros")
start_date = st.sidebar.date_input("Data inicial", df["dateCreated"].min().date())
end_date = st.sidebar.date_input("Data final", df["dateCreated"].max().date())

df_filtrado = df[(df["dateCreated"].dt.date >= start_date) & (df["dateCreated"].dt.date <= end_date)]

# 💳 Tipos de Pagamento
st.subheader("💳 Tipos de Pagamento")
pagamento = df_filtrado["payment_type"].value_counts().reset_index()
pagamento.columns = ["Tipo de Pagamento", "Quantidade"]
fig_pag = px.bar(pagamento, x="Tipo de Pagamento", y="Quantidade", text="Quantidade",
                 title="Tipos de Pagamento", color="Quantidade")
st.plotly_chart(fig_pag, use_container_width=True)

# 🔥 Top 10 Produtos Mais Vendidos
st.subheader("🔥 Top 10 Produtos Mais Vendidos")
produtos = df_filtrado.groupby("item_title")["item_quantity"].sum().sort_values(ascending=False).head(10).reset_index()
fig_prod = px.bar(produtos, x="item_title", y="item_quantity", text="item_quantity",
                  title="Top 10 Produtos Mais Vendidos", color="item_quantity")
fig_prod.update_layout(xaxis_title="Produto", yaxis_title="Quantidade", xaxis_tickangle=-45)
st.plotly_chart(fig_prod, use_container_width=True)

# 📦 Status dos Pedidos
st.subheader("📦 Pedidos por Status")
status = df_filtrado["status"].value_counts().reset_index()
status.columns = ["Status", "Quantidade"]
fig_status = px.bar(status, x="Status", y="Quantidade", text="Quantidade",
                    title="Status dos Pedidos", color="Quantidade")
st.plotly_chart(fig_status, use_container_width=True)


# 📈 Lucro por Produto
st.subheader("📈 Top 10 Produtos por Lucro Total")
df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = df_filtrado.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10).reset_index()
fig_lucro = px.bar(lucro, x="item_title", y="lucro_unitario", text="lucro_unitario",
                   title="Top 10 Produtos por Lucro Total", color="lucro_unitario")
fig_lucro.update_layout(xaxis_title="Produto", yaxis_title="Lucro Total (R$)", xaxis_tickangle=-45)
st.plotly_chart(fig_lucro, use_container_width=True)

# 📄 Dados brutos
if st.checkbox("📄 Mostrar dados brutos"):
    st.dataframe(df_filtrado)
