import json
import requests

def lambda_handler(event, context):
    product_service_url = 'http://ims-product-service.ims-namespace'
    customer_service_url = 'http://ims-customer-service.ims-namespace'
    try:
        method = event.get("requestContext", {}).get("http",{}).get("method", "GET")
        path = event.get("rawPath", "")
        query = event.get("rawQueryString","")
        headers = event.get("headers",{})
        body = event.get("body",None)
        
        if query != "":
            path += "/?"+query
        if "/products" == path[:9]:
            path = product_service_url + path
        else:
            path = customer_service_url + path
        
        response = requests.request(method, path, headers = headers, data = body)
        
        response = {
            'statusCode': response.status_code,
            'headers': dict(response.headers)|{
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response.json())
        }
        return response
    except Exception as e: 
        print(e)
        return {
            'statusCode': 400,
            'headers': {
                    'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "detail":"Request format error at Lambda Function:"+str(e)
            })
        }
