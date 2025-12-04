# __all__ = [
#     "CSVTaskProcessor",]

import os
import json
import logging
from pandas import isna, DataFrame
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from interfaces.google_drive_client import GoogleDriveClient
from interfaces.google_sheet_client import GoogleSheetClient
from controls.property_and_state_manager import (
    TwiceQuota,
    ThreeTimesQuota,
    ReviewReasonByLLM,
    DoNotReviewReason,
    PropertyAndStateManager,
)
from schemas.response_schema import ShareLog, Response
from schemas.llm_schema import Decision, ReviewResult
from schemas.state_schema import CellState, UserState

logger = logging.getLogger("file_sharly")


class CSVTaskProcessor:
    """
    A class to process CSV data and
    Stateful class.
    Binding with csv data, PropertyAndStateManager, GoogleDriveClient and GoogleSheetClient.
    """

    current_date_utc8 = datetime.now(timezone.utc) + timedelta(hours=8)
    this_month = current_date_utc8.month
    today = current_date_utc8.day
    today_str = str(this_month) + "/" + str(today)
    view_limit_strategy_map = {
        "twice_quota": TwiceQuota,
        "three_times_quota": ThreeTimesQuota,
    }
    review_reason_strategy_map = {
        "llm": ReviewReasonByLLM,
        "do_not_review": DoNotReviewReason,
    }
    view_limit_int_map = {
        "twice_quota": 2,
        "three_times_quota": 3,
    }

    def __init__(
        self,
        data_frame: DataFrame,
        course_info_list: list[dict],
        drive_client: GoogleDriveClient,
        sheet_client: GoogleSheetClient,
        view_limit_strategy_str: str,
        review_reason_strategy_str: str,
    ):
        """
        Initialize the CSVTaskProcessor with a GoogleDriveClient and a GoogleSheetClient.

        Args:
            data_frame (DataFrame): Dataframe containing the CSV data.
            course_info_list (list[dict]): The list of dictionaries containing course informations.
            drive_client (GoogleDriveClient): Client to interact with Google Drive API.
            sheet_client (GoogleSheetClient): Client to interact with Google Sheets API.
        """

        self.drive_client = drive_client
        self.sheet_client = sheet_client
        self.data_frame = data_frame
        self.course_info_list = course_info_list
        """               
        list[dict]: [
            {
                "COURSE_BATCH_ID|PK": str=course_batch_id,
                "COURSE_NAME|SK": str,
                "BATCH": str,
                "FileID": str
            },
            ...
        ]
        """
        # now store course_info_list data into this map
        self.file_id_and_course_name_map = {}
        for course_info in course_info_list:
            self.file_id_and_course_name_map[course_info["FileID"]] = course_info.get(
                "SK"
            )

        self.unenrolled_list = self._get_unenrolled_list()
        self.property_and_state_manager = PropertyAndStateManager(
            view_limit_strategy=CSVTaskProcessor.view_limit_strategy_map[
                view_limit_strategy_str
            ],
            review_reason_strategy=CSVTaskProcessor.review_reason_strategy_map[
                review_reason_strategy_str
            ],
        )
        self.view_limit_int = CSVTaskProcessor.view_limit_int_map[
            view_limit_strategy_str
        ]

    @staticmethod
    def _generate_email_message(
        expire_date_utc8: datetime,
        view_limit_near_course_list: list[str],
        view_limit_int: int,
    ) -> str:
        view_limit_near_course_str = " ".join(view_limit_near_course_list)
        reminder_message = (
            f"\
            -----------------------------------------------------------------------\n\
            提醒您：\n\
            由於下列課程： {view_limit_near_course_str} 的申請次數已達{view_limit_int}次，因此上述課程系統將不再開放，\
            若有疑問，歡迎與助教聯絡。\n\
            -----------------------------------------------------------------------\n\n"
            if len(view_limit_near_course_list) > 0
            else ""
        )

        # f-string
        email_message = f"\
            觀看時間至 {expire_date_utc8.month}月{expire_date_utc8.day}日 23:59 UTC+8\n\n\
            【智慧財產權】\n\
            請本人在觀看雲端影片時，嚴禁下載、翻錄雲端影片內容，或是提供給第三人做使用。\n\n\
            【貼心提醒】\n\
            若覺得不清楚的話，建議改用筆電或電腦(螢幕較大之設備)觀看，並且把畫質調成1080p\n\
            (點選「設置」→「畫質」→「1080p」，若無自動調整請重複操作一次)，會比較清楚。\n\n\
            【問題排除】\n\
            * 如遇播放影片時發生問題，請改用「無痕模式」(或「私密瀏覽」...等)試試看，如仍無法觀看請與助教聯繫。\n\n\
            * 如果之後發生「沒有收到補課信件的狀況」怎麼辦？\n\
            1. 檢查有沒有在垃圾郵件\n\
            2. 沒有的話，在 Google Drive（雲端硬碟）的左側欄位，點選「與我共用」\n\
            3. 都沒有看到課程資料夾的話，寄信聯絡助教\n\
            {reminder_message}\
            \n\
            \n\
            補課時遇到的疑難雜症，請參考說明文件：\n\
            https://docs.google.com/document/d/1pAbfLjswXgXTccd1oGM8vDrzm_TP-_Ty/edit\n\
            助教（負責管理雲端）聯絡方式：\n\
            Email: hectopascal.citrus@gmail.com"

        return email_message

    def share_file_with_notifications(self) -> Response:
        google_oauth_token = json.loads(os.getenv("GOOGLE_OAUTH_TOKEN", ""))
        self.drive_client.init_start_file_batch()

        row_size = self.data_frame.shape[0]
        column_size = self.data_frame.shape[1]

        start_time = datetime.now()  # print Log
        """ List of Future objects """
        future_list = []
        """ Map of Future objects to row numbers """
        future_row_map = {}
        """
        List of results of Future objects which are ShareLog.
        ShareLogSchemas in this list are `resluts` already determined to be shared or not,
        but have not been confirmed that it was successfully shared.
        """
        future_result_list = [None] * row_size
        """
        ShareLogSchemas in this list are `resluts` already confirmed that it was successfully shared or not.
        """
        comfirmed_result_list = None

        with ThreadPoolExecutor(max_workers=10) as executor:
            for row in range(row_size):
                future = executor.submit(
                    self._process_single_user_row,
                    row,
                    column_size,
                    google_oauth_token,
                )
                future_list.append(future)
                future_row_map[future] = row
            for future in as_completed(future_list):
                response = future.result()
                """
                If type of response is Response means there is an error, return the error response.
                If type of response is ShareLog means there is ok, continue to next row and save the log.
                """
                if isinstance(response, Response):
                    return response
                elif isinstance(response, ShareLog):
                    row = future_row_map[future]
                    future_result_list[row] = response

        logger.info(
            "_process_single_user_row time: %s", datetime.now() - start_time
        )  # print Log

        start_time = datetime.now()  # print Log
        response = self.drive_client.execute_share_file_batch()
        logger.info(
            "execute_share_file_batch time: %s", datetime.now() - start_time
        )  # print Log
        start_time = datetime.now()  # print Log
        self.sheet_client.execute_write_cells_color_requests()
        logger.info(
            "execute_write_cells_color_requests time: %s", datetime.now() - start_time
        )  # print Log

        """
        Comfirm if requests of sharing files are successful.
        """
        comfirmed_result_list = self.drive_client.comfirm_shared_result(
            future_result_list,
            self.file_id_and_course_name_map,
        )

        """
        If type of response is Response means there is an error when sharing files, return the error response.
        If type of response is None means there is no error when sharing files, return the success response.
        """
        if isinstance(response, Response):
            response.shared_log = comfirmed_result_list
            return response
        else:
            return Response(status="success", shared_log=comfirmed_result_list)

    def _process_single_user_row(
        self, row: int, column_size: int, google_oauth_token
    ) -> ShareLog | Response:
        """
        Processes the data of a single user row, handling one email address per row.

        Args:
            row (int): The index of the row to process in the DataFrame.
            column_size (int): The total number of columns in the DataFrame.
        """
        email_address = self.data_frame.at[row, "電子郵件地址"]
        if isna(email_address):
            email_address = None

        """
        Check if the user has enrolled in the course.
        """
        if not self._if_user_has_enrolled(row):
            logger.info(
                f"row: {row}, email: {email_address} has not enrolled in the course."
            )

            return ShareLog(
                row=row,
                email=email_address,
                shareable_file_id_and_course_name_map={},
            )
        """
        Initialize the state of the user.
        """
        user_state = UserState()

        user_state = self._process_user_cells(
            row,
            column_size,
            google_oauth_token,
            user_state,
        )

        # print(f"user_state.offset: {getattr(user_state, 'offset', 'NOT SET')} in row: {row}")  # debug Log


        """
        Decide whether to share the file with the user.
        """
        if user_state.offset > 0:
            expire_date_utc8 = CSVTaskProcessor.current_date_utc8 + timedelta(
                days=user_state.offset
            )
            expiration_time = (
                f"{expire_date_utc8.strftime('%Y-%m-%d')}T23:59:59+08:00:00"
            )

            email_message = CSVTaskProcessor._generate_email_message(
                expire_date_utc8,
                user_state.view_limit_near_course_name_list,
                self.view_limit_int,
            )

            for (
                shareable_file_id
            ) in user_state.shareable_file_id_and_course_name_map.keys():
                self.drive_client.append_share_file_batch(
                    row,
                    shareable_file_id,
                    email_address,
                    email_message,
                    expiration_time,
                )

            logger.info("row: %s, email: %s", row, email_address)  # print Log
            logger.info(
                "shareable_course_name_list: %s, offset: %s",
                user_state.shareable_file_id_and_course_name_map.values(),
                user_state.offset,
            )  # print Log
            logger.info("-----------------------------------")  # print Log

        return ShareLog(
            row=row,
            email=email_address,
            shareable_file_id_and_course_name_map=user_state.shareable_file_id_and_course_name_map,
            offset=user_state.offset,
            review_result=user_state.review_result,
        )

    def _get_cell_color_thread(
        self, row: int, course_index: int, date_column_index: int, google_oauth_token
    ):
        """
        Q: Why row + 1?
        A: Because after converting sheet into DataFrame,
            row 0 in sheet will be the column names in DataFrame.
            So, row 1 in the sheet will be row 0 in the DataFrame.
        """
        temp_sheet_client = GoogleSheetClient(
            self.sheet_client.spreadsheet_id, google_oauth_token
        )
        return (
            row,
            course_index,
            date_column_index,
            temp_sheet_client.get_cell_color(row + 1, date_column_index),
        )

    def _get_unenrolled_list(self) -> list[str]:
        """
        Get the list of unenrolled users from the Google Sheet.
        """
        # Magic number. Assume the maximum number of unenrolled users is 30.
        assumed_max_unenrolled = 30

        return self.sheet_client.get_cells_value(1, 0, assumed_max_unenrolled)

    def _if_user_has_enrolled(self, row: int) -> bool:
        """
        Check if the user has enrolled in the course.
        """
        user_name_column = 3
        user_name = self.data_frame.iat[row, user_name_column]
        return user_name not in self.unenrolled_list

    def _process_user_cells(
        self, row: int, column_size: int, google_oauth_token, user_state: UserState
    ) -> UserState:
        """
        Process each CellState in the row through parallel processing and return the updated UserState.
        """
        column_date_start_from = 5
        future_list = []

        """
        Scan all cells in the user's row.
        """
        with ThreadPoolExecutor(max_workers=12) as executor:
            for course_index, date_column_index in enumerate(
                range(column_date_start_from, column_size)
            ):
                """
                Check if the date in the cell is today.
                """
                applied_date = self.data_frame.iat[row, date_column_index]
                if applied_date != CSVTaskProcessor.today_str:
                    continue
                """
                Check if:
                1. the course date (in column name) corresponds to the correct course name (in google drive file).
                2. the course name exist (in google drive file).
                """
                course_date = self.data_frame.columns[date_column_index]
                course_name = self.course_info_list[course_index].get("SK")

                if not course_name:
                    continue
                elif course_date not in course_name:
                    return Response(
                        status="error",
                        error_type=f"course date {course_date} corresponds to the wrong course name {course_name}",
                    )

                """
                If all the above conditions are met, create thread to get the cell color of that date.
                """
                future_list.append(
                    executor.submit(
                        self._get_cell_color_thread,
                        row,
                        course_index,
                        date_column_index,
                        google_oauth_token,
                    )
                )

            for task in as_completed(future_list):
                row, course_index, date_column_index, color = task.result()
                red = color["red"]
                green = color["green"]
                blue = color["blue"]

                """
                get the cell state
                """
                cell_state = self.property_and_state_manager.get_cell_state(
                    red, green, blue
                )

                """
                review the reason
                """
                if (
                    cell_state.if_view_limit_near
                    and user_state.review_result.explanation == "尚未初始化。"
                ):
                    user_state.review_result = (
                        self.property_and_state_manager.review_reason_in_cell(
                            row, self.data_frame
                        )
                    )

                """
                get the new user state
                """
                user_state = self.property_and_state_manager.get_updated_user_state(
                    course_index,
                    self.course_info_list,
                    cell_state,
                    user_state,
                )

                """
                update the new cell properties
                """
                self.property_and_state_manager.update_cell_properties(
                    red,
                    green,
                    blue,
                    cell_state,
                    user_state,
                    self.sheet_client,
                    row,
                    date_column_index,
                )
        return user_state
