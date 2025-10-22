import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

from schemas.response_schema import ShareLog, Response

logger = logging.getLogger("file_sharly")


class GoogleDriveClient:
    """
    A class to interact with Google Drive API.
    Stateful class.
    Non Thread-safe class.
    Binding with Google Drive API credentials and batch requests.
    """

    def __init__(
        self,
        credentials_token,
    ):
        GoogleDriveClient.credentials = Credentials.from_authorized_user_info(
            credentials_token, ["https://www.googleapis.com/auth/drive"]
        )
        self.drive_service = build(
            "drive", "v3", credentials=GoogleDriveClient.credentials
        )
        self.batch_requests = None
        self.success_request_id_list = []
        self.backup_drive_request_list = []  # TODO: Solve the deprecated function
        self.if_error_occurred = False

    def _callback(
        self,
        request_id: str,
        response,
        exception,
    ) -> None:
        if exception:
            # Handle error
            logger.error(f"Request_Id: {request_id} failed")
            logger.error(exception)
            self.if_error_occurred = True
        else:
            logger.info(f"Request_Id: {request_id}")
            logger.info(f"Permission Id: {response.get('id')}")
            self.success_request_id_list.append(request_id)
            # TODO: Solve the deprecated function
            # and the might be wrong logic, because
            # The order of the batch request response is not necessarily the same as the order of the requests added.
            # It is recommended to use `request_id` to associate the request and backup data.
            self.backup_drive_request_list.pop(0)

    def init_start_file_batch(self):
        # Initialize batch request
        self.batch_requests = self.drive_service.new_batch_http_request(
            callback=self._callback
        )

    def append_share_file_batch(
        self,
        row: int,
        file_id: str,
        email_address: str,
        email_message: str,
        expiration_time: str,
    ):
        user_permission = {
            "type": "user",
            "role": "reader",
            "expirationTime": expiration_time,
            "emailAddress": email_address,
        }

        self.batch_requests.add(
            self.drive_service.permissions().create(
                fileId=file_id,
                emailMessage=email_message,
                body=user_permission,
                fields="id",
            ),
            request_id=f"{row} {file_id}",
        )

        # TODO: Solve the deprecated function
        self.backup_drive_request_list.append(
            {
                "file_id": file_id,
                "email_message": email_message,
                "body": user_permission,
            }
        )

    def execute_share_file_batch(self) -> Response | None:
        self.batch_requests.execute()
        self.batch_requests = None

        # TODO: Solve the deprecated function
        if self.if_error_occurred:
            return Response(
                status="error",
                error_type="error when sharing files",
                backup_data=self.backup_drive_request_list,
            )

    def comfirm_shared_result(
        self,
        future_result_list: list[ShareLog],
        file_id_and_course_name_map: dict[str, str],
    ) -> list[ShareLog]:
        """
        Check if the file_id of each ShareLog in future_result_list
        can be matched with the request_id in success_request_id_list.

        Arg:
            future_result_list(list[ShareLog]): A list of ShareLog objects that need to be confirmed if they are shared successfully.
            file_id_and_course_name_map(dict[str, str]): A dictionary that maps file_id to course_name.
        Return:
            A list of ShareLog objects that are confirmed if successfully shared or not
        """
        comfirmed_result_list = future_result_list.copy()

        for success_request_id in self.success_request_id_list:
            row, file_id = success_request_id.split(" ")
            row = int(row)

            course_name = file_id_and_course_name_map[file_id]
            logger.debug(
                f"future_result_list[row].shareable_course_name_and_if_successed_map: {future_result_list[row].shareable_course_name_and_if_successed_map}"
            )
            comfirmed_result_list[row].shareable_course_name_and_if_successed_map[course_name] = True
        
        return comfirmed_result_list
