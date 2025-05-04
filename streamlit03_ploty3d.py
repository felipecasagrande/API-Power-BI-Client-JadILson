import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Análise de Vendas", layout="wide")

# Título do dashboard
st.title("Dashboard de Análise de Vendas")

# Função para carregar dados (ajuste o caminho do arquivo conforme necessário)
@st.cache_data
def load_data():
    # Aqui assumimos um arquivo de dados com colunas: Data, Vendas, Lucro, Item, Canal, Preco, Custo, Order_ID
    # Substitua pelo carregamento real dos seus dados
    return pd.read_excel("sales_data.xlsx")

df = load_data()

# Conversão da coluna de data para datetime, se necessário
if not pd.api.types.is_datetime64_any_dtype(df['Data']):
    df['Data'] = pd.to_datetime(df['Data'])

# Sidebar - Filtro de datas (início fixo em 01/01/2025 até hoje)
st.sidebar.header("Filtros")
start_date_default = datetime.date(2025, 1, 1)
end_date_default = datetime.date.today()
selected_date = st.sidebar.date_input("Selecione o intervalo de datas:", [start_date_default, end_date_default])
if isinstance(selected_date, list) and len(selected_date) == 2:
    start_date, end_date = selected_date
else:
    start_date = start_date_default
    end_date = end_date_default

# Garantir que a data inicial não seja anterior a 01/01/2025
if start_date < start_date_default:
    start_date = start_date_default
if end_date < start_date:
    end_date = start_date_default

# Filtrando o DataFrame pelo intervalo de datas selecionado
df_filtered = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

# Cálculo dos KPIs
vendas_total = df_filtered['Vendas'].sum()
lucro_total = df_filtered['Lucro'].sum()

# Calcular Ticket Médio: valor total de vendas dividido pelo número de pedidos
if 'Order_ID' in df_filtered.columns:
    num_pedidos = df_filtered['Order_ID'].nunique()
else:
    num_pedidos = len(df_filtered)
ticket_medio = vendas_total / num_pedidos if num_pedidos > 0 else 0

# Calcular Margem Média (%): (Lucro / Vendas) * 100
margem_media = (lucro_total / vendas_total * 100) if vendas_total > 0 else 0

# Exibir KPIs estilizados com bordas
st.markdown("## Indicadores Principais")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
        <div style="border:2px solid #4CAF50; padding:10px; border-radius:5px;">
            <h4>Total de Vendas</h4>
            <p style="font-size:24px; font-weight:bold;">R$ {vendas_total:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)
with kpi2:
    st.markdown(f"""
        <div style="border:2px solid #2196F3; padding:10px; border-radius:5px;">
            <h4>Total de Lucro</h4>
            <p style="font-size:24px; font-weight:bold;">R$ {lucro_total:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)
with kpi3:
    st.markdown(f"""
        <div style="border:2px solid #FF9800; padding:10px; border-radius:5px;">
            <h4>Ticket Médio</h4>
            <p style="font-size:24px; font-weight:bold;">R$ {ticket_medio:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)
with kpi4:
    st.markdown(f"""
        <div style="border:2px solid #9C27B0; padding:10px; border-radius:5px;">
            <h4>Margem Média</h4>
            <p style="font-size:24px; font-weight:bold;">{margem_media:.2f}%</p>
        </div>
        """, unsafe_allow_html=True)

# Gráfico 1: Evolução de Vendas Diária
st.subheader("Evolução Diária de Vendas")
vendas_diarias = df_filtered.groupby(df_filtered['Data'].dt.date)['Vendas'].sum().reset_index()
fig_vendas_diarias = px.line(vendas_diarias, x='Data', y='Vendas', markers=True,
                             labels={'Data': 'Data', 'Vendas': 'Total de Vendas'})
st.plotly_chart(fig_vendas_diarias, use_container_width=True)

# Gráfico 2: Top 10 Itens por Vendas
st.subheader("Top 10 Itens por Vendas")
top_itens = df_filtered.groupby('Item')['Vendas'].sum().nlargest(10).reset_index()
fig_top_itens = px.bar(top_itens, x='Vendas', y='Item', orientation='h',
                       labels={'Vendas': 'Total de Vendas', 'Item': 'Item'},
                       title='Top 10 Itens')
fig_top_itens.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig_top_itens, use_container_width=True)

# Gráfico 3: Evolução de Lucro Diária
st.subheader("Evolução Diária de Lucro")
lucro_diario = df_filtered.groupby(df_filtered['Data'].dt.date)['Lucro'].sum().reset_index()
fig_lucro_diario = px.line(lucro_diario, x='Data', y='Lucro', markers=True,
                           labels={'Data': 'Data', 'Lucro': 'Lucro Total'})
st.plotly_chart(fig_lucro_diario, use_container_width=True)

# Gráfico 4: Vendas por Canal
st.subheader("Vendas por Canal")
vendas_canal = df_filtered.groupby('Canal')['Vendas'].sum().reset_index()
fig_vendas_canal = px.bar(vendas_canal, x='Canal', y='Vendas',
                          labels={'Canal': 'Canal de Venda', 'Vendas': 'Total de Vendas'},
                          title='Total de Vendas por Canal')
st.plotly_chart(fig_vendas_canal, use_container_width=True)

# Gráfico 5: Evolução Mensal de Vendas
st.subheader("Evolução Mensal de Vendas")
df_filtered['Mes'] = df_filtered['Data'].dt.to_period('M').dt.to_timestamp()
vendas_mensais = df_filtered.groupby('Mes')['Vendas'].sum().reset_index()
fig_vendas_mensais = px.line(vendas_mensais, x='Mes', y='Vendas', markers=True,
                             labels={'Mes': 'Mês', 'Vendas': 'Total de Vendas'})
st.plotly_chart(fig_vendas_mensais, use_container_width=True)

# Gráfico 6: Distribuição de Preço
st.subheader("Distribuição de Preço")
fig_dist_preco = px.histogram(df_filtered, x='Preco', nbins=50,
                              labels={'Preco': 'Preço Unitário'},
                              title='Distribuição dos Preços')
st.plotly_chart(fig_dist_preco, use_container_width=True)

# Gráfico 7: Correlação entre Preço e Custo
st.subheader("Relação entre Preço e Custo (Scatter Plot)")
fig_price_cost = px.scatter(df_filtered, x='Preco', y='Custo',
                            labels={'Preco': 'Preço', 'Custo': 'Custo'},
                            title='Correlação Preço vs Custo')
st.plotly_chart(fig_price_cost, use_container_width=True)

# Gráfico 8: Mapa de Calor de Correlação (Preço, Custo, Vendas, Lucro)
st.subheader("Mapa de Calor de Correlação")
corr = df_filtered[['Preco', 'Custo', 'Vendas', 'Lucro']].corr()
fig_heatmap = px.imshow(corr, text_auto=True, aspect="auto",
                        labels=dict(x="Variáveis", y="Variáveis", color="Correlação"),
                        x=corr.columns, y=corr.columns)
st.plotly_chart(fig_heatmap, use_container_width=True)

# Gráfico 9: Boxplot de Custo
st.subheader("Boxplot de Custo")
fig_box_custo = px.box(df_filtered, y='Custo', points="all",
                       labels={'Custo': 'Custo'})
st.plotly_chart(fig_box_custo, use_container_width=True)

# Exportação de dados filtrados para CSV e Excel
st.subheader("Exportar Dados")
csv_data = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button(label="Baixar CSV", data=csv_data, file_name='dados_filtrados.csv', mime='text/csv')

output = BytesIO()
writer = pd.ExcelWriter(output, engine='xlsxwriter')
df_filtered.to_excel(writer, index=False, sheet_name='Dados')
writer.save()
excel_data = output.getvalue()
st.download_button(label="Baixar Excel", data=excel_data, file_name='dados_filtrados.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
