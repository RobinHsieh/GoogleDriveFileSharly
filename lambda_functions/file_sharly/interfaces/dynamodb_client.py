import boto3
from boto3.dynamodb.conditions import Key


class DynamoDBClient:
    """
    Thread-safe class.
    """

    def __init__(
        self,
        file_id_table_name="FileIDTable",
        spread_sheet_id_table_name="SpreadSheetIDTable",
        response_table_name="ResponseTable",
    ):
        dynamodb = boto3.resource("dynamodb")
        self.file_id_table = dynamodb.Table(file_id_table_name)
        self.spread_sheet_id_table = dynamodb.Table(spread_sheet_id_table_name)
        self.response_table = dynamodb.Table(response_table_name)

    def get_open_course_batch(self) -> list[dict]:
        """
        Get all course batch infos that are open
        Returns:
            list[dict]: [
                {
                    "COURSE_BATCH_ID|PK": str,
                    "WEEK_DAY": str,
                    "BATCH": str,
                    "SPREAD_SHEET_ID": str
                    "IS_OPEN": bool=True
                },
                ...
            ]
        PK: partition key
        """
        scan_kwargs = {"FilterExpression": Key("IS_OPEN").eq(True)}

        items = []
        last_evaluated_key = None

        while True:
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.spread_sheet_id_table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            if "LastEvaluatedKey" in response:
                last_evaluated_key = response["LastEvaluatedKey"]
            else:
                break

        return items

    def get_course(self, course_batch_id: str) -> list[dict]:
        """
        Get course infos from the course batch id
        Args:
            course_batch_id (str): course batch id
        Returns:
            list[dict]: [
                {
                    "COURSE_BATCH_ID|PK": str=course_batch_id,
                    "COURSE_NAME|SK": str,
                    "BATCH": str,
                    "FileID": str
                },
                ...
            ]
        PK: partition key
        SK: sort key
        """
        response = self.file_id_table.query(
            KeyConditionExpression=Key("PK").eq(course_batch_id)
        )
        return response.get("Items", [])

    def save_lambda_response(
        self,
        date: str,
        time: int,
        course_batch_id: str,
        batch_number: str,
        week_day: str,
        response: dict,
        backup_expire_time: int,
    ) -> None:
        self.response_table.put_item(
            Item={
                "Date": date,
                "Time": time,
                "CourseBatchId": course_batch_id,
                "BATCH": batch_number,
                "WEEK_DAY": week_day,
                "Response": response,
                "BackupExpireTime": backup_expire_time,
            }
        )
