import boto3
from boto3.dynamodb.conditions import Key


class DynamoDBClient:
    """
    Thread-safe class.
    """
    def __init__(
        self,
        response_table_name="ResponseTable",
    ):
        dynamodb = boto3.resource("dynamodb")
        self.response_table = dynamodb.Table(response_table_name)

    def get_lambda_response_list(self, date: str) -> list[dict]:
        """
        Get all lambda responses
        Returns:
            list[dict]: [
                {
                    "Date|PK": str,
                    "Time|SK": int,
                    "CourseBatchId": str,
                    "BATCH": str,
                    "WEEK_DAY": str,
                    "Response": dict,
                    "BackupExpireTime": int
                },
                ...
            ]
        """
        response = self.response_table.query(
            KeyConditionExpression=Key("Date").eq(date)
        )
        return response.get("Items", [])
