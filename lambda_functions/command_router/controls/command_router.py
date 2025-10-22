import json
import boto3

from controls.message_factories import NormalMessageResponseCreator

lambda_client = boto3.client("lambda")

# 映射指令到對應 Lambda
command_map = {
    "單堂新增": "GoogleDriveFileSharly-ManageDBFunction-ihSxzeW9dfS1",
    "單堂修改": "GoogleDriveFileSharly-ManageDBFunction-ihSxzeW9dfS1",
    "單堂刪除": "GoogleDriveFileSharly-ManageDBFunction-ihSxzeW9dfS1",
    "梯次設置": "GoogleDriveFileSharly-ManageDBFunction-ihSxzeW9dfS1",
    "梯次資料夾刷新": "GoogleDriveFileSharly-ManageDBFunction-ihSxzeW9dfS1",
    "梯次開關": "GoogleDriveFileSharly-ManageDBFunction-ihSxzeW9dfS1",
    "請假顯示": "GoogleDriveFileSharly-StudentStatusVisualizationFu-7mtxeLyqBf0V",
    "晚到顯示": "GoogleDriveFileSharly-StudentStatusVisualizationFu-7mtxeLyqBf0V",
    "背書顯示": "GoogleDriveFileSharly-StudentStatusVisualizationFu-7mtxeLyqBf0V",
    "寄出結果": "GoogleDriveFileSharly-GetLambdaResponseFunction-v6mSgD0KbMKQ",
    "重新寄出": "GoogleDriveFileSharly-ShareFileFunction-lamffiKXQSz6",  # Deprecated
}


def route_command(command_message):
    message_factory_class = NormalMessageResponseCreator

    tokens = command_message.replace(" ", ",").split(",")
    command = tokens[0]

    target_function = command_map.get(command, "UnknownCommand")

    if target_function == "UnknownCommand":
        body = {
            "message_type": "text",
            "result_message": "【未知指令】請輸入：單堂新增 / 單堂修改 / 單堂刪除 / 梯次設置 / 梯次資料夾刷新 / 梯次開關 / 請假顯示 / 晚到顯示 / 背書顯示 / 寄出結果",
        }

    else:
        try:
            # 同步調用業務 Lambda 並獲取結果
            response = lambda_client.invoke(
                FunctionName=target_function,
                InvocationType="RequestResponse",
                Payload=json.dumps(
                    {
                        "command_message": command_message,
                    }
                ),
            )

            # 解析業務 Lambda 的回傳值
            payload = json.loads(response["Payload"].read())
            body = payload.get("body")

        except Exception as e:
            result_message = f"CommandRouterFunction 系統錯誤： {str(e)}"
            body = {"message_type": "text", "result_message": result_message}

    # 產生回傳訊息
    message_response = message_factory_class.create_message_response(body)
    line_message = message_response.create_line_message()
    return line_message
