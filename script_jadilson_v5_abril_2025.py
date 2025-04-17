import requests
import pandas as pd
from datetime import datetime
import time
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("magis5_log.txt"), logging.StreamHandler()]
)

# Configurações da API
API_BASE_URL = "https://app.magis5.com.br/v1"
API_TOKEN = "4c0a6cbf43944c3da5f6c264f63a7450"
HEADERS = {
    "X-MAGIS5-APIKEY": API_TOKEN,
    "Accept": "application/json"
}

# Parâmetros para a busca de pedidos simples
PARAMS_SIMPLE = {
    "dateSearchType": "created",
    "enableLink": "true",
    "limit": "50",
    "page": "1",
    "status": "all",
    "structureType": "simple",
    "timestampFrom": "1577836800",  # 01/01/2022
    "timestampTo": str(int(time.time()))
}

# Configurações de retry e paralelismo
MAX_RETRIES = 5
BACKOFF_FACTOR = 2
INITIAL_SLEEP = 1
MAX_PAGES = 2
MAX_WORKERS = 10

# Função para verificar conexão com a API
def test_api_connection():
    try:
        response = requests.get(f"{API_BASE_URL}/orders", headers=HEADERS, params={"limit": "1"}, timeout=30)
        if response.status_code == 200:
            logging.info("Conexão com API testada com sucesso")
            return True
        else:
            logging.error(f"Falha na conexão: Status {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Erro de conexão: {e}")
        return False

# Função segura para extrair dados aninhados
def safe_get(data, keys, default=None):
    if data is None:
        return default

    temp = data
    for key in keys:
        if isinstance(temp, dict) and key in temp and temp[key] is not None:
            temp = temp[key]
        else:
            return default
    return temp

# Busca pedidos simples com paginação
def fetch_simple_orders(endpoint, params):
    all_data = []
    page = 1

    while True:  # Processará todas as páginas disponíveis
        params['page'] = str(page)
        url = f"{API_BASE_URL}/{endpoint}"
        logging.info(f"Buscando página {page} de pedidos simples...")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=30)
                response.raise_for_status()  # Lança exceção para status não 2xx
                break
            except requests.exceptions.HTTPError as e:
                logging.error(f"Erro HTTP: {e}")
                if response.status_code in [401, 403]:
                    logging.error("Erro de autenticação - verifique o token API")
                    return all_data
                if attempt == MAX_RETRIES:
                    logging.error(f"Máximo de tentativas atingido para página {page}")
                    return all_data
                sleep_time = INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1))
                logging.info(f"Tentativa {attempt} falhou. Nova tentativa em {sleep_time}s")
                time.sleep(sleep_time)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                logging.error(f"Erro de conexão: {e}")
                if attempt == MAX_RETRIES:
                    return all_data
                time.sleep(INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1)))

        try:
            data = response.json()
            # Validar estrutura da resposta
            if 'orders' not in data:
                logging.error(f"Resposta inesperada da API: {data}")
                break

            orders = data.get('orders', [])

            if not orders:
                logging.info("Nenhum pedido retornado. Finalizando.")
                break

            # Adicionar todos os pedidos, mesmo que não tenham o campo 'id'
            all_data.extend(orders)
            logging.info(f"Página {page}: {len(orders)} pedidos obtidos")

            if len(orders) < int(params.get('limit', 50)):
                logging.info("Última página alcançada")
                break

            page += 1
            time.sleep(0.5)  # Evita throttling da API

        except json.JSONDecodeError:
            logging.error(f"Erro ao decodificar JSON da resposta para página {page}")
            break
        except Exception as e:
            logging.error(f"Erro ao processar resposta: {e}")
            break

    logging.info(f"Total de pedidos simples obtidos: {len(all_data)}")
    return all_data
# Busca detalhes completos de um pedido
def fetch_complete_order(order_id):
    if not order_id:
        logging.warning("ID de pedido vazio recebido")
        return None

    url = f"{API_BASE_URL}/orders/{order_id}"
    logging.info(f"Buscando pedido completo: {order_id}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)

            if response.status_code == 200:
                data = response.json()
                # Validar dados mínimos necessários
                if 'id' not in data:
                    logging.warning(f"Pedido {order_id} sem ID na resposta")
                    return None
                return data
            elif response.status_code == 404:
                logging.warning(f"Pedido {order_id} não encontrado")
                return None
            elif attempt < MAX_RETRIES:
                sleep_time = INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1))
                logging.info(f"Tentativa {attempt} falhou. Nova tentativa em {sleep_time}s")
                time.sleep(sleep_time)
            else:
                logging.error(f"Falha após {MAX_RETRIES} tentativas para pedido {order_id}")
                return None
        except json.JSONDecodeError:
            logging.error(f"Resposta inválida para pedido {order_id}")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1)))
        except Exception as e:
            logging.error(f"Erro ao buscar pedido {order_id}: {e}")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(INITIAL_SLEEP * (BACKOFF_FACTOR ** (attempt - 1)))

# Processa pedidos simples
def process_simple_orders(orders):
    if not orders:
        logging.warning("Nenhum pedido simples para processar")
        return pd.DataFrame()

    processed_data = []
    for order in orders:
        if not isinstance(order, dict):
            logging.warning(f"Pedido em formato inválido: {type(order)}")
            continue

        # CORREÇÃO: Usar completeOrderNumber como ID quando disponível
        order_id = order.get("id", "")
        if not order_id and "completeOrderNumber" in order:
            order_id = order.get("completeOrderNumber", "")

        # Se ainda não tiver ID, tentar extrair da URL do link
        if not order_id and "links" in order and order["links"]:
            for link in order["links"]:
                if link.get("rel") == "self" and link.get("href", "").startswith("/orders/"):
                    order_id = link.get("href").replace("/orders/", "")
                    break

        if not order_id:
            logging.warning("Pedido sem ID encontrado, ignorando")
            continue

        # Extrair dados básicos com valores padrão para campos obrigatórios
        order_data = {
            "id": order_id,
            "externalId": order.get("externalId", ""),
            "status": order.get("status", ""),
            "dateCreated": order.get("dateCreated", ""),
            "storeId": order.get("storeId", ""),
            "channel": order.get("channel", ""),
            "totalValue": order.get("totalValue", 0)
        }

        # Processar links se existirem
        links = order.get("links", [])
        if links:
            for link in links:
                if not isinstance(link, dict):
                    continue

                link_data = order_data.copy()
                link_data.update({
                    "Rel": link.get("rel", ""),
                    "Tipo do Link": link.get("type", ""),
                    "URL do Link": link.get("href", "")
                })
                processed_data.append(link_data)
        else:
            # Se não houver links, adicionar entrada com campos de link vazios
            order_data.update({
                "Rel": "",
                "Tipo do Link": "",
                "URL do Link": ""
            })
            processed_data.append(order_data)

    # Criar DataFrame e garantir que não haja valores NaN
    df = pd.DataFrame(processed_data)
    # Converter valores NaN para strings vazias
    df = df.fillna("")

    logging.info(f"Processados {len(processed_data)} registros de pedidos simples")
    return df

# Processa pedidos completos
def process_complete_order(order):
    if not order:
        return {}

    # Garantir que há um ID de pedido
    order_id = safe_get(order, ["id"], "")
    if not order_id:
        logging.warning("Pedido completo sem ID válido")
        return {}

    # Extrair dados de forma segura
    shipping_address = safe_get(order, ["shipping", "receiverAddress"], {})

    # Processar informações de pagamento
    payment_info = {}
    payments = safe_get(order, ["payments"], [])
    if payments and isinstance(payments, list) and len(payments) > 0:
        payment = payments[0]
        payment_info = {
            "payment_status": safe_get(payment, ["status"], ""),
            "payment_type": safe_get(payment, ["payment_type"], ""),
            "payment_installments": safe_get(payment, ["installments"], 0),
            "payment_amount": safe_get(payment, ["transaction_amount"], 0)
        }

    # Processar informações de itens
    item_info = {}
    items = safe_get(order, ["order_items"], [])
    if items and isinstance(items, list) and len(items) > 0:
        item = items[0]
        item_info = {
            "item_title": safe_get(item, ["item", "title"], ""),
            "item_sku": safe_get(item, ["item", "seller_custom_field"], ""),
            "item_quantity": safe_get(item, ["quantity"], 0),
            "item_price": safe_get(item, ["unit_price"], 0),
            "item_cost": safe_get(item, ["cost"], 0)
        }

    # Montar objeto de pedido completo com valores padrão para evitar NaN
    processed_order = {
        # Dados básicos
        "id": order_id,
        "externalId": safe_get(order, ["externalId"], ""),
        "status": safe_get(order, ["status"], ""),
        "dateCreated": safe_get(order, ["dateCreated"], ""),
        "dateLastUpdated": safe_get(order, ["dateLastUpdated"], ""),
        "totalValue": safe_get(order, ["totalValue"], 0),
        "storeId": safe_get(order, ["storeId"], ""),
        "channel": safe_get(order, ["channel"], ""),

        # Endereço de entrega
        "shipping_street": shipping_address.get("street", ""),
        "shipping_number": shipping_address.get("number", ""),
        "shipping_city": shipping_address.get("city", ""),
        "shipping_state": shipping_address.get("state", ""),
        "shipping_zipcode": shipping_address.get("zipcode", ""),

        # Informações de envio
        "shipping_cost": safe_get(order, ["shipping", "cost"], 0),
        "shipping_type": safe_get(order, ["shipping", "logistic_type"], ""),
        "shipping_tracking": safe_get(order, ["shipping", "logistic", "logisticId"], ""),

        # Adicionar informações de pagamento e item
        **payment_info,
        **item_info
    }

    # Remover valores None
    return {k: (v if v is not None else "") for k, v in processed_order.items()}

# Extrai IDs de pedidos a partir dos links
def extract_order_ids_from_links(simple_orders_df):
    if 'URL do Link' not in simple_orders_df.columns:
        return []

    order_ids = []
    for url in simple_orders_df['URL do Link'].dropna():
        if isinstance(url, str) and url.startswith('/orders/'):
            order_id = url.replace('/orders/', '')
            order_ids.append(order_id)

    return list(set(order_ids))  # Remover duplicatas

# Busca todos os pedidos completos em paralelo
def fetch_all_complete_orders(simple_orders_df):
    if simple_orders_df.empty:
        logging.warning("DataFrame de pedidos simples vazio")
        return []

    # CORREÇÃO: Extrair IDs dos links quando não houver coluna 'id'
    if 'id' not in simple_orders_df.columns or simple_orders_df['id'].isna().all():
        order_ids = extract_order_ids_from_links(simple_orders_df)
        logging.info(f"Extraídos {len(order_ids)} IDs de pedidos a partir dos links")
    else:
        # Garantir que são strings e remover duplicatas
        order_ids = [str(oid).strip() for oid in simple_orders_df['id'].dropna().unique() if str(oid).strip()]

    if not order_ids:
        logging.warning("Nenhum ID de pedido válido encontrado")
        return []

    logging.info(f"Buscando detalhes para {len(order_ids)} pedidos...")

    complete_orders_list = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_order = {executor.submit(fetch_complete_order, order_id): order_id for order_id in order_ids}

        completed = 0
        for future in as_completed(future_to_order):
            order_id = future_to_order[future]
            completed += 1

            if completed % 10 == 0 or completed == len(order_ids):
                logging.info(f"Progresso: {completed}/{len(order_ids)} pedidos ({completed/len(order_ids)*100:.1f}%)")

            try:
                order = future.result()
                if order and isinstance(order, dict) and 'id' in order:
                    processed_order = process_complete_order(order)
                    complete_orders_list.append(processed_order)
                    logging.debug(f"Pedido {order_id} processado com sucesso")
                else:
                    # Adicionar registro mínimo para manter o ID no merge
                    complete_orders_list.append({"id": order_id})
                    logging.warning(f"Pedido {order_id} retornou dados incompletos ou inválidos")
            except Exception as e:
                logging.error(f"Erro ao processar pedido {order_id}: {e}")
                complete_orders_list.append({"id": order_id})

    logging.info(f"Total de {len(complete_orders_list)} pedidos completos processados")
    return complete_orders_list

# Correlaciona pedidos simples e completos
def correlate_orders(simple_df, complete_orders_list):
    if simple_df.empty:
        logging.warning("DataFrame de pedidos simples vazio para correlação")
        return pd.DataFrame(), pd.DataFrame()

    # Garantir que temos dados completos para processar
    if not complete_orders_list:
        logging.warning("Lista de pedidos completos vazia")
        df_complete = pd.DataFrame()
        # Retornar só os dados simples se não tiver dados completos
        return df_complete, simple_df

    # Criar DataFrame de pedidos completos
    df_complete = pd.DataFrame(complete_orders_list)

    # Verificar consistência dos dados
    if 'id' not in df_complete.columns:
        logging.error("DataFrame de pedidos completos não contém coluna 'id'")
        return df_complete, simple_df

    # CORREÇÃO: Se não houver coluna 'id' em simple_df, criar a partir da URL do Link
    if 'id' not in simple_df.columns or simple_df['id'].isna().all():
        logging.info("Criando coluna 'id' a partir da URL do Link")
        simple_df['id'] = simple_df['URL do Link'].apply(
            lambda x: x.replace('/orders/', '') if isinstance(x, str) and x.startswith('/orders/') else ""
        )

    # Garantir que IDs são strings para evitar problemas de tipos no merge
    simple_df['id'] = simple_df['id'].astype(str)
    df_complete['id'] = df_complete['id'].astype(str)

    logging.info(f"Correlacionando {len(simple_df)} pedidos simples com {len(df_complete)} pedidos completos")

    # Fazer merge dos dados
    try:
        combined_df = pd.merge(simple_df, df_complete, on='id', how='left', suffixes=('_simples', '_completos'))
        # Preencher valores NaN com strings vazias
        combined_df = combined_df.fillna("")
        logging.info(f"Correlação concluída: {len(combined_df)} registros")
        return df_complete, combined_df
    except Exception as e:
        logging.error(f"Erro durante a correlação de dados: {e}")
        return df_complete, simple_df

# Salva dados em Excel
def save_to_excel(simple_df, complete_df, combined_df, filename="relatorio_magis5_v5.0.xlsx"):
    try:
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Garantir que DataFrames não estão vazios e preparar para salvar
            # if not simple_df.empty:
            #     # Preencher NaN com strings vazias
            #     simple_df_clean = simple_df.fillna("")
            #     simple_df_clean.to_excel(writer, sheet_name='Simples', index=False)
            #     logging.info(f"Planilha 'Simples' salva com {len(simple_df_clean)} registros")

            if not complete_df.empty:
                # Preencher NaN com strings vazias
                complete_df_clean = complete_df.fillna("")
                complete_df_clean.to_excel(writer, sheet_name='Completo', index=False)
                logging.info(f"Planilha 'Completo' salva com {len(complete_df_clean)} registros")

            # if not combined_df.empty:
            #     # Preencher NaN com strings vazias
            #     combined_df_clean = combined_df.fillna("")
            #     combined_df_clean.to_excel(writer, sheet_name='Combinado', index=False)
            #     logging.info(f"Planilha 'Combinado' salva com {len(combined_df_clean)} registros")

        logging.info(f"Dados salvos em {filename}")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar Excel: {e}")
        return False

# Função principal
def main():
    try:
        logging.info("Iniciando extração de dados Magis5")

        # Testar conexão com API
        if not test_api_connection():
            logging.critical("Falha na conexão com API. Verificar Token e disponibilidade.")
            return False

        # Buscar pedidos simples
        simple_orders = fetch_simple_orders("orders", PARAMS_SIMPLE)
        if not simple_orders:
            logging.error("Nenhum pedido simples encontrado.")
            return False

        # Processar pedidos simples
        df_simple = process_simple_orders(simple_orders)
        if df_simple.empty:
            logging.error("Processamento de pedidos simples resultou vazio.")
            return False

        # Salvar backup dos dados simples
        save_to_excel(df_simple, pd.DataFrame(), pd.DataFrame(), "magis5_simples_backup.xlsx")
        logging.info(f"Backup dos dados simples salvos. Total: {len(df_simple)} registros")

        # Buscar e processar pedidos completos
        complete_orders_list = fetch_all_complete_orders(df_simple)
        if not complete_orders_list:
            logging.warning("Nenhum pedido completo encontrado. Salvando apenas dados simples.")
            save_to_excel(df_simple, pd.DataFrame(), pd.DataFrame())
            return True

        # Correlacionar dados
        df_complete, df_combined = correlate_orders(df_simple, complete_orders_list)

        # Salvar resultado final
        if save_to_excel(df_simple, df_complete, df_combined):
            logging.info("Processo concluído com sucesso!")
            return True
        else:
            logging.error("Falha ao salvar dados.")
            return False

    except Exception as e:
        logging.critical(f"Erro inesperado: {e}")
        import traceback
        logging.critical(traceback.format_exc())
        return False

if __name__ == "__main__":
    main()
