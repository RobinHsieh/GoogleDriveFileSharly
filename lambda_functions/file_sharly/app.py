import os
import json
import logging
import threading
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from interfaces import (
    dynamodb_client,
    google_drive_client,
    google_sheet_client,
)
from controls import csv_task_processor, backup_processor

logger = logging.getLogger("file_sharly")
logger.handlers.clear()  # 清除現有 handlers
logger.propagate = False  # 防止 log 傳遞到 root logger

console_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # Get time
    current_date_utc8 = datetime.now(timezone.utc) + timedelta(hours=8)
    # format date "MM/DD", ex: "09/01"
    today_str = current_date_utc8.strftime("%m/%d")

    # Get Google OAuth Token
    google_oauth_token = json.loads(os.getenv("GOOGLE_OAUTH_TOKEN", ""))

    # Init DynamoDB
    dynamodb_service = dynamodb_client.DynamoDBClient()

    # Start the job
    if event.get("command_message", "") != "重新寄出":

        def job_thread(course_batch):
            course_batch_id = course_batch.get("PK")
            spreadsheet_id = course_batch.get("SPREAD_SHEET_ID")
            week_day = course_batch.get("WEEK_DAY")
            batch_number = course_batch.get("BATCH")
            view_limit_strategy_str = course_batch.get("VIEW_LIMIT_STRATEGY")
            review_reason_strategy_str = course_batch.get("REVIEW_REASON_STRATEGY")

            drive_client = google_drive_client.GoogleDriveClient(google_oauth_token)

            sheet_client = google_sheet_client.GoogleSheetClient(
                spreadsheet_id, google_oauth_token
            )
            start_time = datetime.now()  # print Log
            sheet_data_frame = sheet_client.get_sheet_as_data_frame()
            logger.info(
                "sheet_data_frame time: %s", datetime.now() - start_time
            )  # print Log

            sheet_client.append_write_cells_color_request(
                0, 23, sheet_data_frame.shape[0] + 1, 0.8, 0.8, 0.8
            )
            start_time = datetime.now()  # print Log
            sheet_client.execute_write_cells_color_requests()
            logger.info(
                "execute_write_cells_color_requests time: %s",
                datetime.now() - start_time,
            )  # print Log

            logger.info(
                f"@.@ *_* >o< @.@ *_* >o< @.@ *_* >o<| week-day{week_day} {batch_number} is going to sharing..."
            )
            course_list = dynamodb_service.get_course(course_batch_id)
            csv_processor = csv_task_processor.CSVTaskProcessor(
                sheet_data_frame,
                course_list,
                drive_client,
                sheet_client,
                view_limit_strategy_str,
                review_reason_strategy_str,
            )
            response = csv_processor.share_file_with_notifications()
            dynamodb_service.save_lambda_response(
                today_str,
                int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp()),
                course_batch_id,
                batch_number,
                week_day,
                response.model_dump(),
                int((datetime.now(timezone.utc) + timedelta(hours=18)).timestamp()),
            )

        logger.info(
            f"Start--------------------------------------------------------------------- {today_str}"
        )

        open_course_batch_list = dynamodb_service.get_open_course_batch()

        thread_list = []
        for course_batch in open_course_batch_list:
            thread = threading.Thread(target=job_thread, args=(course_batch,))
            thread_list.append(thread)
            thread.start()

        for thread in thread_list:
            thread.join()

        logger.info(
            f"End----------------------------------------------------------------------- {today_str}"
        )

    elif event.get("command_message", "") == "重新寄出":
        """
        Deprecated
        TODO: Remove get_backup_drive_request
        """

        def job_thread(backup_drive_request_list):
            drive_client = google_drive_client.GoogleDriveClient(google_oauth_token)
            backup_processor_instance = backup_processor.BackupProcessor(drive_client)
            backup_processor_instance.share_file_with_notifications(
                backup_drive_request_list
            )

        logger.info(
            f"Backup Start-------------------------------------------------------------- {today_str}"
        )

        # backup_drive_request_info_list = dynamodb_service.get_backup_drive_request()

        # thread_list = []
        # for backup_drive_request_info in backup_drive_request_info_list:
        #     backup_drive_request_list = backup_drive_request_info.get(
        #         "BackupDriveRequestList"
        #     )
        #     thread = threading.Thread(
        #         target=job_thread, args=(backup_drive_request_list,)
        #     )
        #     thread_list.append(thread)
        #     thread.start()

        # for thread in thread_list:
        #     thread.join()

        logger.info(
            f"Backup End---------------------------------------------------------------- {today_str}"
        )

        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": "重寄成功！ Deprecated"},
        }
