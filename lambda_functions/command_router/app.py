import os
import json
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
)

from controls import command_router


CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN", None)
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET", None)

# init LINE SDK
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_message = command_router.route_command(event.message.text)
    line_bot_api.reply_message(event.reply_token, line_message)


def lambda_handler(event, context):
    # get X-Line-Signature header value
    signature = event["headers"]["x-line-signature"]

    # get request body
    body = event["body"]

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return {
            "statusCode": 502,
            "body": json.dumps(
                "Invalid signature. Please check your channel access token/channel secret."
            ),
        }
    return {"statusCode": 200, "body": json.dumps("Hello from Lambda!")}
