import os
import json
from datetime import datetime, timedelta, timezone
from interfaces import googe_sheet_client, dynamodb_client
from controls.visualize import leave_status, late_arrival_status, recital_selection


# Get Google OAuth Token
GOOGLE_OAUTH_TOKEN = json.loads(os.getenv("GOOGLE_OAUTH_TOKEN", ""))

# Init DynamoDB
dynamodb_service = dynamodb_client.DynamoDBClient()

# Get time
current_date_utc8 = datetime.now(timezone.utc) + timedelta(hours=8)
# format date "MM/DD", ex: "09/01"
target_date = current_date_utc8.strftime("%m/%d")


def lambda_handler(event, context):
    command_message = event["command_message"]
    tokens = command_message.split(" ")
    course_batch_id = tokens[1]

    spread_sheet_id = dynamodb_service.get_spread_sheet_id(course_batch_id)

    # === 1. 讀取請假資料 ===
    sheet_client = googe_sheet_client.GoogleSheetClient(
        spreadsheet_id=spread_sheet_id,
        credentials_token=GOOGLE_OAUTH_TOKEN,
    )

    if tokens[0] == "請假顯示":
        result = leave_status(sheet_client, target_date)
    elif tokens[0] == "晚到顯示":
        result = late_arrival_status(sheet_client, target_date)
    elif tokens[0] == "背書顯示":
        result = recital_selection(sheet_client, target_date)

    return result
