import datetime
import json
import requests

class TransactionProperties:
    id = "id"
    date = "date"
    customerId = "customerId"
    buyOrSell = "buyOrSell"
    totalAmount = "totalAmount"
    items = "items"
    productId = "productId"
    quantity = "quantity"
    rate = "rate"
    name = "name"
    originalQuantity = "originalQuantity"
    originalRate = "originalRate"
    originalUsedInTransaction = "originalUsedInTransaction"
    usedInTransaction = "usedInTransaction"
    avgRate = "avgBuyRate"
    toRollback = "toRollback"
    

def call_product_service(product, action, headers):
    # Return Flag, json result
    product_service_url = "http://ims-product-service.ims-namespace/products/"
    if action == "BUY":
        product_service_url += "add_quantity_product"
    elif action == "SELL":
        product_service_url += "del_quantity_product"
    response = requests.request(
        "PUT",
        product_service_url,
        headers = {
            "authorization": headers["authorization"],
            "content-type": 'application/json'
        },
        data = json.dumps({
            TransactionProperties.id: product[TransactionProperties.productId],
            TransactionProperties.quantity: product[TransactionProperties.quantity],
            TransactionProperties.avgRate: product[TransactionProperties.rate]
        })
    )
    if response.status_code == 200:
        return True, response.json()
    return False, response.json()

def call_customer_service(customer_id, headers):
    # Return Flag, json result
    customer_service_url = "http://ims-customer-service.ims-namespace/customers/customer_add_in_transaction"
    response = requests.request(
        "PUT",
        customer_service_url,
        headers = {
            "authorization": headers["authorization"],
            "content-type": 'application/json'
        },
        data = json.dumps({
            TransactionProperties.id: customer_id
        })
    )
    if response.status_code == 200:
        return True, response.json()
    return False, response.json()

def call_transaction_service(event):
    transaction_service_url = "http://ims-transaction-service.ims-namespace/transactions/add_transaction"
    response = requests.request(
        "POST",
        transaction_service_url,
        headers = event.get("headers", {}),
        data = event.get("body", None)
    )
    if response.status_code == 200:
        return True, response
    return False, response

def rollback_product(product, action, headers):
    product_service_url = "http://ims-product-service.ims-namespace/products/rollback_quantity_product"
    response = requests.request(
        "PUT",
        product_service_url,
        headers = {
            "authorization": headers["authorization"],
            "content-type": 'application/json'
        },
        data = json.dumps({
            TransactionProperties.id: product[TransactionProperties.productId],
            TransactionProperties.quantity: product[TransactionProperties.originalQuantity],
            TransactionProperties.avgRate: product[TransactionProperties.originalRate],
            TransactionProperties.usedInTransaction: product[TransactionProperties.originalUsedInTransaction]
        }))
    return response.json()
    
def rollback_customer(customer, headers):
    customer_service_url = "http://ims-customer-service.ims-namespace/customers/customer_rollback_in_transaction"
    response = requests.request(
        "PUT",
        customer_service_url,
        headers = {
            "authorization": headers["authorization"],
            "content-type": 'application/json'
        },
        data = json.dumps({
            TransactionProperties.id: customer[TransactionProperties.customerId],
            TransactionProperties.usedInTransaction: customer[TransactionProperties.originalUsedInTransaction]
        })
    )
    return response.json()
    

def validate_transaction(transaction):
    transaction[TransactionProperties.date] = datetime.datetime.strptime(transaction[TransactionProperties.date], "%Y-%m-%d").date()
    transaction[TransactionProperties.customerId] = int(transaction[TransactionProperties.customerId])
    transaction[TransactionProperties.totalAmount] = round(float(transaction[TransactionProperties.totalAmount]),4)
    assert transaction[TransactionProperties.totalAmount] != 0
    assert transaction[TransactionProperties.buyOrSell] == "BUY" or transaction[TransactionProperties.buyOrSell] == "SELL"
    assert type(transaction[TransactionProperties.items]) == list and len(transaction[TransactionProperties.items]) > 0
    totalCost = 0
    for item in transaction[TransactionProperties.items]:
        item[TransactionProperties.productId] = int(item[TransactionProperties.productId])
        item[TransactionProperties.quantity] = round(float(item[TransactionProperties.quantity]),4)
        item[TransactionProperties.rate] = round(float(item[TransactionProperties.rate]),4)
        totalCost += item[TransactionProperties.quantity] * item[TransactionProperties.rate]
    assert round(totalCost, 4) == transaction[TransactionProperties.totalAmount]

def lambda_handler(event, context):
    # TODO implement
    try:
        transaction = json.loads(event["body"])
        headers = event["headers"]
        try:
            validate_transaction(transaction)
        except Exception as e:
            print(e)
            return {
                'statusCode': 400,
                'headers': {
                    'content-type': 'application/json'
                },
                'body': json.dumps({
                    "detail": "Invalid format of Transaction:"+type(e).__name__+":"+str(e)
                })
            }
        rollback = False
        rollback_msg = ""
        prodIdToName = dict()
        for item in transaction[TransactionProperties.items]:
            flag, product = call_product_service(item, transaction[TransactionProperties.buyOrSell], headers)
            if not flag:
                rollback = True
                rollback_msg = "Product Rollback: "+str(item[TransactionProperties.productId])+": "+product["detail"]
                break
            prodIdToName[item[TransactionProperties.productId]] = product[TransactionProperties.name]
            item[TransactionProperties.originalRate] = product[TransactionProperties.avgRate]
            item[TransactionProperties.originalQuantity] = product[TransactionProperties.quantity]
            item[TransactionProperties.originalUsedInTransaction] = product[TransactionProperties.usedInTransaction]
            item[TransactionProperties.toRollback] = True
        if not rollback:
            flag, customer = call_customer_service(transaction[TransactionProperties.customerId], headers)
            if not flag:
                rollback = True
                rollback_msg = "Customer Rollback: "+str(transaction[TransactionProperties.customerId])+": "+customer["detail"]
            else:
                transaction[TransactionProperties.name] = customer[TransactionProperties.name] 
                transaction[TransactionProperties.originalUsedInTransaction] = customer[TransactionProperties.usedInTransaction]
                transaction[TransactionProperties.toRollback] = True
        if not rollback:
            flag,result_transaction_response = call_transaction_service(event)
            if not flag:
                rollback = True
                rollback_msg = "Transaction Rollback: "+result_transaction.json()["detail"]
        if rollback:
            if transaction.get(TransactionProperties.toRollback, False):
                rollback_customer(transaction, headers)
            for item in transaction[TransactionProperties.items]:
                if item.get(TransactionProperties.toRollback, False):
                    rollback_product(item, transaction[TransactionProperties.buyOrSell], headers)
            return {
                'statusCode': 400,
                'headers': {
                    'content-type': 'application/json'
                },
                'body': json.dumps({
                    'detail': rollback_msg
                })
            }

        result_transaction = result_transaction_response.json()
        result_transaction[TransactionProperties.name] = transaction[TransactionProperties.name]
        for item in result_transaction[TransactionProperties.items]:
            item[TransactionProperties.name] = prodIdToName.get(item[TransactionProperties.productId],None)
        return {
            'statusCode': 200,
            'headers': dict(result_transaction_response.headers),
            'body': json.dumps(result_transaction)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 400,
            'headers': {
                    'content-type': 'application/json'
            },
            'body': json.dumps({
                "detail": "Request format error at Lambda Function:"+type(e).__name__+":"+str(e)
            })
        }