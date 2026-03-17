import boto3
import os
import json
import requests

REGION_NAME = os.getenv("AWS_REGION", "us-east-1")
WORKER_LAMBDA_NAME = os.getenv("WORKER_LAMBDA_NAME", "NutriVisionAnalysisFunction")

lambda_client = boto3.client('lambda', region_name=REGION_NAME)

def invoke_worker_lambda(payload: dict) -> dict:
    """
    Invokes the existing Worker AWS Lambda function via boto3.
    Passes the action, context and profile data in the payload.
    Uses 'RequestResponse' to wait for the AI execution.
    """
    try:
        response = lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Read and parse the Lambda response payload
        response_payload = json.loads(response['Payload'].read().decode("utf-8"))
        
        # Check if the worker lambda threw an error
        if "errorMessage" in response_payload:
            raise Exception(f"Worker Lambda Error: {response_payload['errorMessage']}")
            
        return response_payload
    except Exception as e:
        print(f"Error invoking worker lambda: {e}")
        raise e

def lookup_openfoodfacts(barcode: str) -> dict:
    """Calls OpenFoodFacts API for Barcode lookup"""
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('status') == 1:
            product = data.get('product', {})
            return {
                "product_name": product.get('product_name', 'Unknown'),
                "ingredients": product.get('ingredients_text', 'Unknown'),
                "nutrition_data": product.get('nutriments', {})
            }
        else:
            return None
    except Exception as e:
        print(f"Error calling OpenFoodFacts: {e}")
        return None
import boto3
import os
import json
import requests

REGION_NAME = os.getenv("AWS_REGION", "us-east-1")
WORKER_LAMBDA_NAME = os.getenv("WORKER_LAMBDA_NAME", "nutrivision-worker")

lambda_client = boto3.client('lambda', region_name=REGION_NAME)

def invoke_worker_lambda(payload: dict) -> dict:
    """
    Invokes the existing Worker AWS Lambda function via boto3.
    Passes the action, context and profile data in the payload.
    Uses 'RequestResponse' to wait for the AI execution.
    """
    try:
        response = lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Read and parse the Lambda response payload
        response_payload = json.loads(response['Payload'].read().decode("utf-8"))
        
        # Check if the worker lambda threw an error
        if "errorMessage" in response_payload:
            raise Exception(f"Worker Lambda Error: {response_payload['errorMessage']}")
            
        return response_payload
    except Exception as e:
        print(f"Error invoking worker lambda: {e}")
        raise e

def lookup_openfoodfacts(barcode: str) -> dict:
    """Calls OpenFoodFacts API for Barcode lookup"""
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('status') == 1:
            product = data.get('product', {})
            return {
                "product_name": product.get('product_name', 'Unknown'),
                "ingredients": product.get('ingredients_text', 'Unknown'),
                "nutrition_data": product.get('nutriments', {})
            }
        else:
            return None
    except Exception as e:
        print(f"Error calling OpenFoodFacts: {e}")
        return None
