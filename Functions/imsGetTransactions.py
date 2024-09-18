import json
import requests

def call_product_service(id, headers):
    product_service_url = "http://ims-product-service.ims-namespace/products/get_product/"+str(id)
    response = requests.request(
        "GET",
        product_service_url,
        headers = {
            "authorization": headers["authorization"],
            "content-type": 'application/json'
        }
    )
    return response.json()

def call_customer_service(id, headers):
    customer_service_url = "http://ims-customer-service.ims-namespace/customers/get_customer/"+str(id)
    response = requests.request(
        "GET",
        customer_service_url,
        headers = {
            "authorization": headers["authorization"],
            "content-type": 'application/json'
        }
    )
    return response.json()

def lambda_handler(event, context):
    
    transaction_service_url = "http://ims-transaction-service.ims-namespace"
    
    try:
        path = event["rawPath"]
        query = event.get("rawQueryString","")
        headers = dict(event.get("headers", {}))
        response = requests.request(
            "GET",
            transaction_service_url + path + "?" + query,
            headers = headers
        )
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': json.dumps(response.json())
            }
        portfolio = response.json()
        if len(portfolio.get("transactionsList", [])) > 0:
            transactionsList = portfolio.get("transactionsList")
            if "productId" in transactionsList[0]:
                for item in transactionsList:
                    product = call_product_service(item["productId"], headers)
                    item["name"] = product.get("name", None)
                    if "transaction" in item and item["transaction"] is not None:
                        customer = call_customer_service(item["transaction"]["customerId"], headers)
                        item["transaction"]["name"] = customer.get("name", None)
            elif "customerId" in transactionsList[0]:
                for item in transactionsList:
                    customer = call_customer_service(item["customerId"], headers)
                    item["name"] = customer.get("name", None)
        return {
            'statusCode': 200,
            'headers': dict(response.headers),
            'body': json.dumps(portfolio)
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'headers': {
                'content-type': 'application/json'
            },
            "body": json.dumps({
                "detail": "Exception raised in Lambda function:"+type(e).__name__+":"+str(e)
            })
        }