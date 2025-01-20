

import requests
import pandas as pd
from datetime import datetime
import time
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações
API_BASE_URL = "https://app.magis5.com.br/v1"
API_TOKEN = "4c0a6cbf43944c3da5f6c264f63a7450"  # **Mantenha sua API_TOKEN segura!**
HEADERS = {
    "X-MAGIS5-APIKEY": API_TOKEN,
    "Accept": "application/json"
}

# Parâmetros para a chamada simples
PARAMS_SIMPLE = {
    "dateSearchType": "simple",
    "enableLink": "true",
    "limit": "50",
    "page": "1",
    "status": "all",
    "structureType": "simple",
    "timestampFrom": "1641006000",
    "timestampTo": str(int(time.time()))
}

# Configurações de retentativa
MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # Exponential backoff factor
INITIAL_SLEEP = 1    # Initial sleep time in seconds

# Número máximo de páginas para evitar loops infinitos
MAX_PAGES = 20000
# MAX_PAGES = 500

# Configurações de programação paralela
MAX_WORKERS = 10  # Número máximo de threads paralelas para buscar detalhes completos

# Função para buscar dados com paginação e retentativa
def fetch_simple_orders(endpoint, params):
    """
    Busca todos os dados de pedidos simples com paginação e retentativas em caso de falhas.
    """
    all_data = []
    page = 1

    while True:
        if page > MAX_PAGES:
            print(f"Alcançado o número máximo de páginas ({MAX_PAGES}). Finalizando busca de pedidos simples.")
            break

        params['page'] = str(page)
        url = f"{API_BASE_URL}/{endpoint}"
        print(f"Buscando página {page} de pedidos simples...")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=30)
                if response.status_code == 200:
                    break  # Sucesso, sair do loop de retentativas
                else:
                    print(f"Erro ao buscar dados simples: {response.status_code} - {response.text}")
                    # Se erro do servidor (5xx), tentar novamente
                    if 500 <= response.status_code < 600:
                        raise requests.exceptions.HTTPError(f"Erro do servidor: {response.status_code}")
                    else:
                        # Erros do cliente (4xx) provavelmente não serão resolvidos com retentativas
                        return all_data
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                print(f"Attempt {attempt} falhou com erro: {e}")
                if attempt < MAX_RETRIES:
                    sleep_time = INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1))
                    print(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    print(f"Falha ao buscar página {page} após {MAX_RETRIES} tentativas. Finalizando busca de pedidos simples.")
                    return all_data

        try:
            data = response.json()
        except ValueError:
            print("Erro ao decodificar a resposta JSON dos pedidos simples.")
            break

        orders = data.get('orders', [])
        if not orders:
            print("Nenhum dado simples retornado. Finalizando busca de pedidos simples...")
            break

        all_data.extend(orders)
        print(f"Página {page} retornou {len(orders)} registros de pedidos simples.")

        # Verificar se há mais páginas
        if len(orders) < int(params.get('limit', 50)):
            print("Última página de pedidos simples alcançada.")
            break

        page += 1
        # Respeitar limites de taxa da API (se aplicável)
        time.sleep(0.1)  # Ajuste o tempo conforme necessário

    return all_data

# Função para buscar detalhes completos de um pedido com retentativa
def fetch_complete_order(complete_order_number):
    """
    Busca os detalhes completos de um pedido específico com retentativas em caso de falhas.
    """
    url = f"{API_BASE_URL}/orders/{complete_order_number}"
    print(f"Buscando detalhes completos para o pedido: {complete_order_number}...")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                try:
                    order = response.json()
                    return order
                except ValueError:
                    print(f"Erro ao decodificar a resposta JSON do pedido {complete_order_number}.")
                    return None
            else:
                print(f"Erro ao buscar detalhes do pedido {complete_order_number}: {response.status_code} - {response.text}")
                if 500 <= response.status_code < 600:
                    raise requests.exceptions.HTTPError(f"Erro do servidor: {response.status_code}")
                else:
                    # Erros do cliente (4xx) provavelmente não serão resolvidos com retentativas
                    return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
            print(f"Attempt {attempt} falhou com erro: {e}")
            if attempt < MAX_RETRIES:
                sleep_time = INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1))
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"Falha ao buscar detalhes do pedido {complete_order_number} após {MAX_RETRIES} tentativas.")
                return None

# Função para processar dados simples
def process_simple_orders(orders):
    """
    Processa os dados dos pedidos simples e cria um DataFrame com os campos desejados.
    """
    processed_data = []
    for order in orders:
        complete_order_number = order.get("completeOrderNumber", "")
        links = order.get("links", [])

        # Extrair informações dos links
        for link in links:
            rel = link.get("rel", "")
            link_type = link.get("type", "")
            href = link.get("href", "")
            processed_data.append({
                "completeOrderNumber": complete_order_number,
                "Rel": rel,
                "Tipo do Link": link_type,
                "URL do Link": href
            })

    return pd.DataFrame(processed_data)

# Função para processar dados completos
def process_complete_order(order):
    """
    Processa os dados completos de um único pedido e retorna um dicionário.
    """
    if not order:
        return {}

    processed_order = {
        "externalId": order.get("externalId", ""),
        "id": order.get("id", ""),
        "status": order.get("status", ""),
        "subStatus": order.get("subStatus", ""),
        "dateCreated": order.get("dateCreated", ""),
        "dateDelivered": order.get("dateDelivered", ""),
        "totalValue": order.get("totalValue", 0),
        "totalWeight": order.get("totalWeight", 0),
        "channel": order.get("channel", ""),
        "channelName": order.get("channelName", ""),
        "fulfilled": order.get("fulfilled", False),
        "hasStock": order.get("hasStock", False),
        "hasAccount": order.get("hasAccount", False),
        # Adicione mais campos conforme necessário
        "buyer_first_name": order.get("buyer", {}).get("first_name", ""),
        "buyer_email": order.get("buyer", {}).get("email", ""),
        "buyer_last_name": order.get("buyer", {}).get("last_name", ""),
        "buyer_full_name": order.get("buyer", {}).get("full_name", ""),
        "buyer_phone_number": order.get("buyer", {}).get("phone", {}).get("number", ""),
        "buyer_alternative_phone_number": order.get("buyer", {}).get("alternative_phone", {}).get("number", ""),
        "order_item_title": order.get("order_items", [{}])[0].get("item", {}).get("title", "") if order.get("order_items") else "",
        
        "Imagem": order.get("order_items", [{}])[0].get("item", {}).get("defaultPicture", ""),
        "Data do pedido": order.get("dateCreated", ""),
        "Número pedido": order.get("id", ""),
        "Número pedido ERP": order.get("erpId", ""),
        "Número carrinho": order.get("externalId", ""),
        "Loja": order.get("storeId", ""),
        "Status": order.get("status", ""),
        "SKU": order.get("order_items", [{}])[0].get("item", {}).get("seller_custom_field", ""),
        "Id Canal Marketplace": order.get("channel", ""),
        "Título": order.get("order_items", [{}])[0].get("item", {}).get("title", ""),
        "Custo total produto": order.get("orderConciliation", {}).get("totalCost", 0),
        "Custo do produto": order.get("order_items", [{}])[0].get("cost", 0),
        "Valor unitário venda": order.get("order_items", [{}])[0].get("unit_price", 0),
        "Quantidade": order.get("order_items", [{}])[0].get("quantity", 0),
        "Custo envio": order.get("shipping", {}).get("cost", 0),
        "Custo envio seller": order.get("orderConciliation", {}).get("freightToPay", 0),
        "Valor total pedido": order.get("totalValue", 0),
        "Valor total produto": order.get("order_items", [{}])[0].get("unit_price", 0) * order.get("order_items", [{}])[0].get("quantity", 0),
        "Tipo logística": order.get("shipping", {}).get("logistic_type", ""),
        "Rastreio": order.get("shipping", {}).get("logistic", {}).get("logisticId", ""),
                
        
        "payment_status": order.get("payments", [{}])[0].get("status", "") if order.get("payments") else "",
        "payment_type": order.get("payments", [{}])[0].get("payment_type", "") if order.get("payments") else "",
        "payment_installments": order.get("payments", [{}])[0].get("installments", 0) if order.get("payments") else 0,
        "payment_transaction_amount": order.get("payments", [{}])[0].get("transaction_amount", 0) if order.get("payments") else 0
    }

    return processed_order

# Função para salvar dados em Excel com múltiplas abas
def save_to_excel(simple_df, complete_df, combined_df, filename="relatorio_magis5_v2.0.xlsx"):
    """
    Salva os dados em um arquivo Excel com abas separadas para simples, completo e combinado.
    """
    try:
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            simple_df.to_excel(writer, sheet_name='Simples', index=False)
            complete_df.to_excel(writer, sheet_name='Completo', index=False)
            combined_df.to_excel(writer, sheet_name='Combinado', index=False)
        print(f"Dados salvos em: {filename}")
    except Exception as e:
        print(f"Erro ao salvar os dados no Excel: {e}")

# Função para correlacionar os pedidos simples com os detalhes completos
def correlate_orders(simple_orders_df, complete_orders_list):
    """
    Correlaciona os pedidos simples com os pedidos completos com base no completeOrderNumber e externalId.
    Retorna DataFrames para pedidos completos e combinados.
    """
    # Criar DataFrame para pedidos completos
    if complete_orders_list:
        df_complete = pd.DataFrame(complete_orders_list)
    else:
        df_complete = pd.DataFrame()

    # Merge entre simples e completos com base em completeOrderNumber = externalId
    combined_df = pd.merge(simple_orders_df, df_complete, left_on='completeOrderNumber', right_on='externalId', how='left', suffixes=('_simples', '_completos'))

    return df_complete, combined_df

# Função para buscar detalhes completos em paralelo
def fetch_all_complete_orders(simple_orders_df):
    """
    Busca detalhes completos de todos os pedidos simples utilizando programação paralela.
    """
    complete_orders_list = []
    complete_order_numbers = simple_orders_df['completeOrderNumber'].unique()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Criar um dicionário para mapear futures a complete_order_numbers
        future_to_order = {executor.submit(fetch_complete_order, order_num): order_num for order_num in complete_order_numbers}

        for future in as_completed(future_to_order):
            order_num = future_to_order[future]
            try:
                order = future.result()
                if order:
                    processed_complete_order = process_complete_order(order)
                    complete_orders_list.append(processed_complete_order)
                else:
                    # Caso não consiga obter detalhes completos, adiciona um dicionário vazio ou com informações limitadas
                    complete_orders_list.append({
                        "externalId": order_num,
                        "id": "",
                        "status": "",
                        "subStatus": "",
                        "dateCreated": "",
                        "dateDelivered": "",
                        "totalValue": 0,
                        "totalWeight": 0,
                        "channel": "",
                        "channelName": "",
                        "fulfilled": False,
                        "hasStock": False,
                        "hasAccount": False,
                        "buyer_first_name": "",
                        "buyer_email": "",
                        "buyer_last_name": "",
                        "buyer_full_name": "",
                        "buyer_phone_number": "",
                        "buyer_alternative_phone_number": "",
                        "order_item_title": "",
                        "payment_status": "",
                        "payment_type": "",
                        "payment_installments": 0,
                        "payment_transaction_amount": 0,
                        "Imagem": "",
                        "Data do pedido": "",
                        "Número pedido": "",
                        "Número pedido ERP": "",
                        "Número carrinho": "",
                        "Loja": "",
                        "Status": "",
                        "SKU": "",
                        "Id Canal Marketplace": "",
                        "Título": "",
                        "Custo total produto": "",
                        "Custo do produto": "",
                        "Valor unitário venda": "",
                        "Quantidade": "",
                        "Custo envio": "",
                        "Custo envio seller": "",
                        "Valor total pedido": "",
                        "Valor total produto": "",
                        "Tipo logística": "",
                        "Rastreio": "",
                    })
            except Exception as e:
                print(f"Erro ao processar o pedido {order_num}: {e}")
                complete_orders_list.append({
                    "externalId": order_num,
                    "id": "",
                    "status": "",
                    "subStatus": "",
                    "dateCreated": "",
                    "dateDelivered": "",
                    "totalValue": 0,
                    "totalWeight": 0,
                    "channel": "",
                    "channelName": "",
                    "fulfilled": False,
                    "hasStock": False,
                    "hasAccount": False,
                    "buyer_first_name": "",
                    "buyer_email": "",
                    "buyer_last_name": "",
                    "buyer_full_name": "",
                    "buyer_phone_number": "",
                    "buyer_alternative_phone_number": "",
                    "order_item_title": "",
                    "payment_status": "",
                    "payment_type": "",
                    "payment_installments": 0,
                    "payment_transaction_amount": 0,
                    "Imagem": "",
                    "Data do pedido": "",
                    "Número pedido": "",
                    "Número pedido ERP": "",
                    "Número carrinho": "",
                    "Loja": "",
                    "Status": "",
                    "SKU": "",
                    "Id Canal Marketplace": "",
                    "Título": "",
                    "Custo total produto": "",
                    "Custo do produto": "",
                    "Valor unitário venda": "",
                    "Quantidade": "",
                    "Custo envio": "",
                    "Custo envio seller": "",
                    "Valor total pedido": "",
                    "Valor total produto": "",
                    "Tipo logística": "",
                    "Rastreio": ""
                })

    return complete_orders_list

# Fluxo principal
def main():
    print("Iniciando a busca de pedidos simples...")
    simple_orders = fetch_simple_orders("orders", PARAMS_SIMPLE)

    if not simple_orders:
        print("Nenhum pedido simples encontrado. Finalizando o script.")
        return
    else:
        print(f"Total de pedidos simples obtidos: {len(simple_orders)}")
        print("Processando pedidos simples...")
        df_simple = process_simple_orders(simple_orders)

    print("\nIniciando a busca de detalhes completos para cada pedido simples utilizando programação paralela...")
    complete_orders_list = fetch_all_complete_orders(df_simple)

    if not complete_orders_list:
        print("Nenhum pedido completo obtido.")
        df_complete = pd.DataFrame()
    else:
        print(f"Total de pedidos completos obtidos: {len(complete_orders_list)}")
        print("Processando pedidos completos...")

    # Correlacionar os pedidos simples com os completos
    print("\nCorrelacionando os pedidos simples com os detalhes completos...")
    df_complete, df_combined = correlate_orders(df_simple, complete_orders_list)

    if df_combined.empty:
        print("Nenhum dado combinado para salvar no Excel.")
        return

    # Salvar os dados em Excel
    print("Salvando dados no Excel...")
    save_to_excel(df_simple, df_complete, df_combined)
    print("Processo concluído!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        sys.exit(1)
