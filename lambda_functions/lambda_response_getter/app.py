from datetime import (
    datetime,
    timedelta,
    timezone,
)
from interfaces import dynamodb_client
from controls import flex_render


def lambda_handler(event, context):
    # Get time
    current_date_utc8 = datetime.now(timezone.utc) + timedelta(hours=8)
    # format date "MM/DD", ex: "09/01"
    today_str = current_date_utc8.strftime("%m/%d")

    # Init DynamoDB
    dynamodb_service = dynamodb_client.DynamoDBClient()
    lambda_response_list = dynamodb_service.get_lambda_response_list(today_str)

    flex_content = flex_render.create_flex_message(lambda_response_list)
    print(flex_content)

    return {
        "statusCode": 200,
        "body": {"message_type": "flex", "result_message": flex_content},
    }
