from interfaces.google_drive_client import GoogleDriveClient


class BackupProcessor:
    def __init__(
        self,
        drive_client: GoogleDriveClient,
    ):
        self.drive_client = drive_client

    def share_file_with_notifications(self, backup_drive_request_list):
        self.drive_client.init_start_file_batch()
        for backup_drive_request in backup_drive_request_list:
            file_id = backup_drive_request.get("file_id")
            email_address = backup_drive_request.get("emailAddress")
            email_message = backup_drive_request.get("email_message")
            expiration_time = backup_drive_request.get("expirationTime")
            self.drive_client.append_share_file_batch(
                file_id, email_address, email_message, expiration_time
            )
        self.drive_client.execute_share_file_batch()
