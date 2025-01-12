import requests
import pandas as pd
from datetime import datetime
import time

# Configurações
API_BASE_URL = "https://app.magis5.com.br/v1"
API_TOKEN = "4c0a6cbf43944c3da5f6c264f63a7450"
HEADERS = {
    "X-MAGIS5-APIKEY": API_TOKEN,
    "Accept": "application/json"
}

# Ajuste do limite para 20 e `structureType` para "simple"
PARAMS_ORDERS = {
    "dateSearchType": "simple",
    "enableLink": "true",
    "limit": "20",
    "page": "1",
    "status": "all",
    "structureType": "simple",
    "timestampFrom": "1641006000",
    "timestampTo": str(int(time.time()))
}

# Função para buscar dados com paginação e re-tentativas
def fetch_all_data(endpoint, params, max_retries=3):
    """
    Busca todos os dados de um endpoint com paginação.
    """
    all_data = []
    page = 1
    retries = 0

    while True:
        params['page'] = str(page)
        url = f"{API_BASE_URL}/{endpoint}"
        print(f"Buscando página {page} de {endpoint}...")

        while retries < max_retries:
            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=60)  # 60 segundos de timeout
                if response.status_code != 200:
                    print(f"Erro ao buscar dados: {response.status_code} - {response.text}")
                    retries += 1
                    time.sleep(2)
                    continue

                data = response.json()
                items = data.get('orders', [])
                if not items:
                    print("Nenhum dado retornado. Finalizando...")
                    break

                all_data.extend(items)
                print(f"Página {page} retornou {len(items)} registros.")
                break

            except requests.exceptions.RequestException as e:
                print(f"Erro na requisição: {e}")
                retries += 1
                time.sleep(2)

        if retries == max_retries:
            print("Número máximo de re-tentativas alcançado. Abortando...")
            break

        # Verificar se há mais páginas
        if len(items) < int(params['limit']):
            print("Última página alcançada.")
            break

        page += 1

    return all_data

# Função para processar dados e gerar DataFrame
def process_orders(orders):
    """
    Processa os dados dos pedidos e cria um DataFrame com os campos desejados.
    """
    processed_data = []
    for order in orders:
        for item in order.get("order_items", []):
            processed_data.append({
                "Imagem": item.get("item", {}).get("defaultPicture", ""),
                "Data do pedido": order.get("dateCreated", ""),
                "Número pedido": order.get("id", ""),
                "Número pedido ERP": order.get("erpId", ""),
                "Número carrinho": order.get("externalId", ""),
                "Loja": order.get("storeId", ""),
                "Status": order.get("status", ""),
                "SKU": item.get("item", {}).get("seller_custom_field", ""),
                "Id Canal Marketplace": order.get("channel", ""),
                "Título": item.get("item", {}).get("title", ""),
                "Custo total produto": order.get("orderConciliation", {}).get("totalCost", 0),
                "Custo do produto": item.get("cost", 0),
                "Valor unitário venda": item.get("unit_price", 0),
                "Quantidade": item.get("quantity", 0),
                "Custo envio": order.get("shipping", {}).get("cost", 0),
                "Custo envio seller": order.get("orderConciliation", {}).get("freightToPay", 0),
                "Valor total pedido": order.get("totalValue", 0),
                "Valor total produto": item.get("unit_price", 0) * item.get("quantity", 0),
                "custo total produto": order.get("orderConciliation", {}).get("totalCost", 0),
                "Tipo logística": order.get("shipping", {}).get("logistic_type", ""),
                "Rastreio": order.get("shipping", {}).get("logistic", {}).get("logisticId", "")
            })
    return pd.DataFrame(processed_data)

# Função para salvar dados em Excel com nome baseado na data e hora atual
def save_to_excel(dataframe, filename_prefix="relatorio_magis5"):
    """
    Salva os dados em um arquivo Excel com nome baseado na data e hora atual.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.xlsx"

    try:
        dataframe.to_excel(filename, index=False)
        print(f"Dados salvos em: {filename}")
    except Exception as e:
        print(f"Erro ao salvar os dados no Excel: {e}")

# Fluxo principal
def main():
    print("Iniciando a busca de pedidos...")
    orders = fetch_all_data("orders", PARAMS_ORDERS)

    if not orders:
        print("Nenhum pedido encontrado.")
        return

    print(f"Total de pedidos obtidos: {len(orders)}")

    print("Processando pedidos...")
    df_orders = process_orders(orders)

    if df_orders.empty:
        print("Nenhum dado para salvar no Excel.")
        return

    print("Salvando dados no Excel...")
    save_to_excel(df_orders)
    print("Processo concluído!")

if __name__ == "__main__":
    main()
