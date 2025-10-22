import boto3
import json

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("SpreadSheetIDTable")

def lambda_handler(event, context):

    items = table.scan().get("Items", [])

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            # "Access-Control-Allow-Origin": "https://robinhsieh.github.io",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(items)
    }
