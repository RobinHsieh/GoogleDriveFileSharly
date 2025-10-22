import json

from interfaces.dynamodb_client import DynamoDBClient


dynamodb_client = DynamoDBClient()


def lambda_handler(event, context):
    command_message = event["command_message"]
    result_message = dynamodb_client.command_line(command_message)

    return {"statusCode": 200, "body": {"message_type": "text", "result_message": result_message}}
