import os
import json
import boto3
from boto3.dynamodb.conditions import Key

from interfaces.google_drive_client import GoogleDriveClient


class DynamoDBClient:
    def __init__(
        self,
        file_id_table_name="FileIDTable",
        folder_id_table_name="FolderIDTable",
        spread_sheet_id_table_name="SpreadSheetIDTable",
    ):
        dynamodb = boto3.resource("dynamodb")
        self.file_id_table = dynamodb.Table(file_id_table_name)
        self.folder_id_table = dynamodb.Table(folder_id_table_name)
        self.spread_sheet_id_table = dynamodb.Table(spread_sheet_id_table_name)

        self.add_course = AddCourse(self.file_id_table)
        self.update_course = UpdateCourse(self.file_id_table)
        self.delete_course = DeleteCourse(self.file_id_table)
        self.add_course_batch = AddCourseBatch(
            self.folder_id_table, self.spread_sheet_id_table
        )
        self.update_course_batch = UpdateCourseBatch(
            self.file_id_table, self.folder_id_table
        )
        self.toggle_course_batch_status = ToggleCourseBatchStatus(
            self.spread_sheet_id_table
        )
        # self.unknown_command = UnknownCommand()

        self.command_action_map = {
            "單堂新增": self.add_course,
            "單堂修改": self.update_course,
            "單堂刪除": self.delete_course,
            "梯次設置": self.add_course_batch,
            "梯次資料夾刷新": self.update_course_batch,
            "梯次開關": self.toggle_course_batch_status,
        }

    def command_line(self, user_message: str) -> str:
        tokens = user_message.replace(" ", ",").split(",")
        command = tokens[0]
        action = self.command_action_map.get(command)
        return action(tokens)


class AddCourse:
    def __init__(self, file_id_table):
        self.file_id_table = file_id_table

    def __call__(self, tokens: list[str]) -> str:
        if len(tokens) < 4:
            return "【參數不足】格式應為: 單堂新增 梯次代碼 單堂日期 FileID"

        course_batch_id, lesson_date, file_id = tokens[1], tokens[2], tokens[3]
        self.file_id_table.put_item(
            Item={"PK": course_batch_id, "SK": lesson_date, "FileID": file_id}
        )
        return f"梯次代碼 {course_batch_id}\n單堂　　 {lesson_date}\n已新增！"


class UpdateCourse:
    def __init__(self, file_id_table):
        self.file_id_table = file_id_table

    def __call__(self, tokens: list[str]) -> str:
        if len(tokens) < 4:
            return "【參數不足】格式應為: 單堂修改 梯次代碼 單堂日期 FileID"

        course_batch_id, lesson_date, file_id = tokens[1], tokens[2], tokens[3]
        self.file_id_table.update_item(
            Key={"PK": course_batch_id, "SK": lesson_date},
            UpdateExpression="SET FileID = :file_id",
            ExpressionAttributeValues={":file_id": file_id},
        )
        return f"梯次代碼 {course_batch_id}\n單堂　　 {lesson_date}\n已修改！"


class DeleteCourse:
    def __init__(self, file_id_table):
        self.file_id_table = file_id_table

    def __call__(self, tokens: list[str]) -> str:
        if len(tokens) < 3:
            return "【參數不足】格式應為: 單堂刪除 梯次代碼 單堂日期"

        course_batch_id, lesson_date = tokens[1], tokens[2]
        self.file_id_table.delete_item(Key={"PK": course_batch_id, "SK": lesson_date})
        return f"梯次代碼 {course_batch_id}\n單堂　　 {lesson_date}\n已刪除！"


class AddCourseBatch:
    def __init__(self, folder_id_table, spread_sheet_id_table):
        self.folder_id_table = folder_id_table
        self.spread_sheet_id_table = spread_sheet_id_table

    def __call__(self, tokens: list[str]) -> str:
        if len(tokens) < 6:
            return "【參數不足】格式應為: 梯次設置 梯次代碼 星期 梯次 SPREAD_SHEET_ID FOLDER_ID 補課次數規則（twice_quota, three_times_quota） 理由審核規則（llm, do_not_review）"

        (
            course_batch_id,
            week_day,
            batch_number,
            spreadsheet_id,
            folder_id,
            view_limit_strategy_str,
            review_reason_strategy_str,
        ) = (
            tokens[1],
            tokens[2],
            tokens[3],
            tokens[4],
            tokens[5],
            tokens[6],
            tokens[7],
        )

        self.folder_id_table.put_item(
            Item={"PK": course_batch_id, "FolderID": folder_id}
        )
        self.spread_sheet_id_table.put_item(
            Item={
                "PK": course_batch_id,
                "WEEK_DAY": week_day,
                "BATCH": batch_number,
                "SPREAD_SHEET_ID": spreadsheet_id,
                "IS_OPEN": True,
                "VIEW_LIMIT_STRATEGY": view_limit_strategy_str,
                "REVIEW_REASON_STRATEGY": review_reason_strategy_str,
            }
        )
        return f"梯次代碼 {course_batch_id}\n星期　　 {week_day}\n梯次　　 {batch_number}\n已設置！"


class UpdateCourseBatch:
    def __init__(self, file_id_table, folder_id_table):
        self.file_id_table = file_id_table
        self.folder_id_table = folder_id_table

        self.drive_service = GoogleDriveClient(
            json.loads(os.getenv("GOOGLE_OAUTH_TOKEN", None))
        )

    def __call__(self, tokens: list[str]) -> str:
        if len(tokens) < 2:
            return "【參數不足】格式應為: 梯次資料夾刷新 梯次代碼"

        course_batch_id = tokens[1]

        """
        get file ids and file names from dynamodb
        """
        file_dict_list_from_dynamodb = self.file_id_table.query(
            KeyConditionExpression=Key("PK").eq(course_batch_id)
        )["Items"]

        """
        get folder id from dynamodb
        """
        folder_dict_from_dynamodb = self.folder_id_table.get_item(
            Key={"PK": course_batch_id}
        ).get("Item")
        if not folder_dict_from_dynamodb:
            return f"【數據缺失】梯次代碼 {course_batch_id}\n尚未創建！"
        folder_id_from_dynamodb = folder_dict_from_dynamodb["FolderID"]

        """
        get file ids and file names from google drive
        """
        file_dict_list_from_drive = self.drive_service.list_files_info(
            folder_id_from_dynamodb
        )
        file_temp_dict_list_from_dynamodb = file_dict_list_from_dynamodb.copy()

        return_message = ""

        """
        以 google drive 為準，更新 dynamodb
        """
        for file_dict_from_drive in file_dict_list_from_drive:
            file_name_from_drive = file_dict_from_drive["name"]
            file_id_from_drive = file_dict_from_drive["id"]

            # 情況 1：資料完全一致，不需要更新
            matched_item = next(
                (
                    file_dict_from_dynamodb
                    for file_dict_from_dynamodb in file_dict_list_from_dynamodb
                    if file_dict_from_dynamodb.get("SK") == file_name_from_drive
                    and file_dict_from_dynamodb.get("FileID") == file_id_from_drive
                ),
                None,
            )
            if matched_item:
                file_temp_dict_list_from_dynamodb.remove(matched_item)
                return_message += f"梯次代碼 {course_batch_id}\n單堂　　 {file_name_from_drive}\n無需更新！\n"
                continue  # 確保不進入後面的條件

            # 情況 2：名稱相符但 file id 不同，進行更新
            matched_item = next(
                (
                    file_dict_from_dynamodb
                    for file_dict_from_dynamodb in file_dict_list_from_dynamodb
                    if file_dict_from_dynamodb.get("SK") == file_name_from_drive
                    and file_dict_from_dynamodb.get("FileID") != file_id_from_drive
                ),
                None,
            )
            if matched_item:
                self.file_id_table.update_item(
                    Key={"PK": course_batch_id, "SK": file_name_from_drive},
                    UpdateExpression="SET FileID = :file_id",
                    ExpressionAttributeValues={":file_id": file_id_from_drive},
                )
                file_temp_dict_list_from_dynamodb.remove(matched_item)
                return_message += f"梯次代碼 {course_batch_id}\n單堂　　 {file_name_from_drive}\n已修改對應 file id！\n"
                continue

            # 情況 3：在 DynamoDB 中找不到該名稱，進行新增
            # 注意：此處無法從 file_dict_list_from_dynamodb 找到對應項目，因此不需要移除
            self.file_id_table.put_item(
                Item={
                    "PK": course_batch_id,
                    "SK": file_name_from_drive,
                    "FileID": file_id_from_drive,
                }
            )
            return_message += f"梯次代碼 {course_batch_id}\n單堂　　 {file_name_from_drive}\n已新增！\n"

        # 處理在 DynamoDB 中但不在 Google Drive 中的資料（刪除）
        for file_dict_from_dynamodb in file_temp_dict_list_from_dynamodb:
            file_name_from_dynamodb = file_dict_from_dynamodb.get("SK")
            self.file_id_table.delete_item(
                Key={"PK": course_batch_id, "SK": file_name_from_dynamodb}
            )
            return_message += f"梯次代碼 {course_batch_id}\n單堂　　 {file_name_from_dynamodb}\n已刪除！\n"

        return return_message


class ToggleCourseBatchStatus:
    def __init__(self, spread_sheet_id_table):
        self.spread_sheet_id_table = spread_sheet_id_table

    def __call__(self, tokens: list[str]) -> str:
        if len(tokens) < 3:
            return "【參數不足】格式應為: 梯次開關 開啟/關閉 梯次代碼"
        if tokens[1] == "開啟":
            is_open = True
        elif tokens[1] == "關閉":
            is_open = False
        else:
            return "【參數錯誤】格式應為: 梯次開關 開啟/關閉 梯次代碼"

        course_batch_id = tokens[2]
        self.spread_sheet_id_table.update_item(
            Key={"PK": course_batch_id},
            UpdateExpression="SET IS_OPEN = :is_open",
            ExpressionAttributeValues={":is_open": is_open},
        )
        return f"梯次代碼 {course_batch_id}\n已{tokens[1]}！"
