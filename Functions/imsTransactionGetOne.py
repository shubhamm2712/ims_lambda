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
    # TODO implement
    transaction_service_url = "http://ims-transaction-service.ims-namespace"
    
    try:
        path = event["rawPath"]
        headers = dict(event.get("headers", {}))
        response = requests.request(
            "GET",
            transaction_service_url + path,
            headers = headers
        )
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': json.dumps(response.json())
            }
        transaction = response.json()
        customer = call_customer_service(transaction["customerId"], headers)
        transaction["name"] = customer.get("name", None)
        for item in transaction["items"]:
            product = call_product_service(item["productId"], headers)
            item["name"] = product.get("name", None)
        return {
            'statusCode': 200,
            'headers': dict(response.headers),
            'body': json.dumps(transaction)
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