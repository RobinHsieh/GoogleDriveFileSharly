import boto3


class DynamoDBClient:
    def __init__(
        self,
        spread_sheet_id_table_name="SpreadSheetIDTable",
    ):
        dynamodb = boto3.resource("dynamodb")

        self.spread_sheet_id_table = dynamodb.Table(spread_sheet_id_table_name)

    def get_spread_sheet_id(self, course_batch_id: str) -> str:
        """
        Get spread sheet id from the course batch id
        Args:
            course_batch_id (str): course batch id
        Returns:
            spread_sheet_id (str): spread sheet id
        """
        response = self.spread_sheet_id_table.get_item(
            Key={
                "PK": course_batch_id,
            }
        )
        return response["Item"]["SPREAD_SHEET_ID"]
