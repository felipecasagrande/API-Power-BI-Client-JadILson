import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Configurações iniciais
st.set_page_config(page_title="Dashboard Magis5", layout="wide")
st.title("📦 Dashboard Magis5 - Relatório de Vendas")
sns.set_theme(style="whitegrid")

# 🔽 Leitura do arquivo CSV
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
st.subheader("💳 Tipos de Pagamento (Seaborn)")
pagamento = df_filtrado["payment_type"].value_counts().reset_index()
pagamento.columns = ["Tipo de Pagamento", "Quantidade"]
fig1, ax1 = plt.subplots()
sns.barplot(data=pagamento, x="Tipo de Pagamento", y="Quantidade", palette="viridis", ax=ax1)
ax1.set_title("Tipos de Pagamento")
ax1.set_xticklabels(ax1.get_xticklabels(), rotation=90)
st.pyplot(fig1)

# 🔥 Top 10 Produtos Mais Vendidos
st.subheader("🔥 Top 10 Produtos Mais Vendidos (Seaborn)")
produtos = df_filtrado.groupby("item_title")["item_quantity"].sum().sort_values(ascending=False).head(10).reset_index()
fig2, ax2 = plt.subplots(figsize=(10, 6))
sns.barplot(data=produtos, x="item_quantity", y="item_title", palette="crest", ax=ax2)
ax2.set_title("Top 10 Produtos Mais Vendidos")
ax2.set_xlabel("Quantidade")
ax2.set_ylabel("Produto")
st.pyplot(fig2)

# 📦 Status dos Pedidos
st.subheader("📦 Pedidos por Status (Seaborn)")
status = df_filtrado["status"].value_counts().reset_index()
status.columns = ["Status", "Quantidade"]
fig3, ax3 = plt.subplots()
sns.barplot(data=status, x="Status", y="Quantidade", palette="flare", ax=ax3)
ax3.set_title("Status dos Pedidos")
ax3.set_xticklabels(ax3.get_xticklabels(), rotation=90)
st.pyplot(fig3)

# 🗺️ Pedidos por Estado (UF)
if "shipping_state" in df_filtrado.columns:
    st.subheader("🗺️ Pedidos por Estado (Seaborn)")
    estado = df_filtrado["shipping_state"].value_counts().reset_index()
    estado.columns = ["Estado", "Quantidade"]
    fig4, ax4 = plt.subplots(figsize=(12, 6))
    sns.barplot(data=estado, x="Quantidade", y="Estado", palette="light:b", ax=ax4)
    ax4.set_title("Pedidos por Estado")
    st.pyplot(fig4)

# 📈 Lucro por Produto
st.subheader("📈 Top 10 Produtos por Lucro Total (Seaborn)")
df_filtrado["lucro_unitario"] = df_filtrado["item_price"] - df_filtrado["item_cost"]
lucro = df_filtrado.groupby("item_title")["lucro_unitario"].sum().sort_values(ascending=False).head(10).reset_index()
fig5, ax5 = plt.subplots(figsize=(10, 6))
sns.barplot(data=lucro, x="lucro_unitario", y="item_title", palette="mako", ax=ax5)
ax5.set_title("Top 10 Produtos por Lucro Total")
ax5.set_xlabel("Lucro Total (R$)")
ax5.set_ylabel("Produto")
st.pyplot(fig5)

# 📄 Dados brutos
if st.checkbox("📄 Mostrar dados brutos"):
    st.dataframe(df_filtrado)
