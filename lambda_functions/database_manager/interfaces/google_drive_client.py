from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleDriveClient:
    """
    A class to interact with Google Drive API.
    Stateful class.
    Binding with Google Drive API credentials and batch requests.
    """

    def __init__(
        self,
        credentials_token,
    ):
        GoogleDriveClient.credentials = Credentials.from_authorized_user_info(
            credentials_token, ["https://www.googleapis.com/auth/drive"]
        )
        GoogleDriveClient.drive_service = build(
            "drive", "v3", credentials=GoogleDriveClient.credentials
        )

    def list_files_info(self, folder_id: str) -> list[dict[str, str]]:
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = (
            GoogleDriveClient.drive_service.files()
            .list(q=query, pageSize=20, fields="nextPageToken, files(id, name)")
            .execute()
        )
        # print("results:", results)
        items = results.get("files", [])
        # print("items:", items)
        # if not items:
        #     print("No files found.")
        #     return None
        return items
