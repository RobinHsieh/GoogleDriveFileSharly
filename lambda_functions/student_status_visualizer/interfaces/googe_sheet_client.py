import io
import csv
from pandas import DataFrame, read_csv

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetClient:
    """
    A class to interact with Google Sheets API.
    Stateful class.
    Binding with Google Sheets API credentials, requests and sheet.
    Guides: https://developers.google.com/sheets/api/reference/rest
    """

    def __init__(self, spreadsheet_id, credentials_token):
        """
        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            credentials_token (str): The path to the credentials token file.
        """
        self.spreadsheet_id = spreadsheet_id

        # Load credentials and initialize Google Sheets API client
        GoogleSheetClient.credentials = Credentials.from_authorized_user_info(
            credentials_token, ["https://www.googleapis.com/auth/drive"]
        )
        self.sheets_service = build(
            "sheets", "v4", credentials=GoogleSheetClient.credentials
        )

        self.sheet_name_id_dict = {}

        self.write_cell_color_requests_list = []

    def get_sheet_as_data_frame(self, sheet_name="課後雲端") -> DataFrame:
        """
        Fetches the data from a Google Sheet and writes it to DataFrame.
        Cell values in row 1 of sheet will convert to column names in DataFrame.
        Guides: https://developers.google.com/sheets/api/guides/values#read
        Returns:
            data_frame (DataFrame)
        """

        # Get the data from the specified sheet
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=sheet_name)
            .execute()
        )
        rows = result.get("values", [])

        # Write the data to a CSV string
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        csv_string = output.getvalue()
        output.close()

        data_frame = read_csv(
            io.StringIO(csv_string),
            sep=",",
            skip_blank_lines=False,
        )

        return data_frame

    def _get_sheet_id(self, sheet_name) -> str:
        """
        Fetches the ID of a specific sheet within a spreadsheet.
        Returns:
            sheet_id(str): The ID of the sheet.
        """
        if sheet_name in self.sheet_name_id_dict:
            return self.sheet_name_id_dict[sheet_name]
        else:
            sheets_metadata = (
                self.sheets_service.spreadsheets()
                .get(spreadsheetId=self.spreadsheet_id, fields="sheets(properties)")
                .execute()
            )

            sheets = sheets_metadata.get("sheets", "")
            sheet_id = None
            for sheet in sheets:
                if sheet["properties"]["title"] == sheet_name:
                    sheet_id = sheet["properties"]["sheetId"]
                    break
            self.sheet_name_id_dict[sheet_name] = sheet_id
            return sheet_id

    def append_write_cells_color_request(
        self, row, column, row_range, red, green, blue, sheet_name="課後雲端"
    ):
        """
        Updates the background color of a range of cells in a Google Sheet.
        Guides: https://developers.google.com/sheets/api/guides/values?hl=zh-tw#python
        Args:
            row (int): The starting row index.
            column (int): The starting column index.
            row_range (int): The number of cells in a row to update.
            red (float): The red component of the color interval [0, 1].
            green (float): The green component of the color interval [0, 1].
            blue (float): The blue component of the color interval [0, 1].
            sheet_name (str): The name of the sheet to update.
        """
        sheet_id = self._get_sheet_id(sheet_name)

        # Prepare a list of cell values with the desired background color
        cell_values = [
            {
                "userEnteredFormat": {
                    "backgroundColor": {"red": red, "green": green, "blue": blue}
                }
            }
        ] * row_range

        # Create list containing each cells value in a row
        row_list = [{"values": cell_value} for cell_value in cell_values]

        requests = {
            "updateCells": {
                "rows": row_list,
                "fields": "userEnteredFormat.backgroundColor",
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + row_range,
                    "startColumnIndex": column,
                    "endColumnIndex": column + 1,
                },
            }
        }
        self.write_cell_color_requests_list.append(requests)

    def execute_write_cells_color_requests(self):
        """
        Executes a batch of write cell format requests.
        """
        body = {"requests": self.write_cell_color_requests_list}
        try:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body=body
            ).execute()
        except HttpError as error:
            print(f"An error occurred: {error}")  # Debungging

    def get_cell_color(self, row, column, sheet_name="課後雲端") -> dict[str:float]:
        """
        Fetches the background color of a specific cell in a Google Sheet.
        Args:
            row (int): The row index of the cell.
            column (int): The column index of the cell.
        Returns:
            color (dict): The RGB color of the cell.
        """
        request = self.sheets_service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id,
            ranges=sheet_name,
            fields=
            'sheets('
                'data('
                    'rowData('
                        'values('
                            'userEnteredFormat('
                                'backgroundColor'
                            ')'
                        ')'
                    ')'
                ')'
            ')',
        )
        result = request.execute()

        sheet_data = result["sheets"][0]["data"][0]["rowData"][row]["values"][column]
        color = sheet_data.get("userEnteredFormat", {}).get("backgroundColor", {})

        return {
            "red": color.get("red", 0),
            "green": color.get("green", 0),
            "blue": color.get("blue", 0),
        }

    def _column_index_to_a1(self, index):
        """
        Converts a column index to a1 notation.
        Args:
            index (int): The column index.
        Returns:
            str: The corresponding a1 notation of the column.
        """
        letter = ""
        while index >= 0:
            letter = chr(index % 26 + 65) + letter
            index = index // 26 - 1
        return letter

    def get_cells_value(self, row, column, row_range, sheet_name="未續報") -> list[str]:
        """
        Fetches the values of a range of cells in a Google Sheet.
        Guides: https://developers.google.com/sheets/api/samples/reading
        Args:
            row (int): The starting row index.
            column (int): The starting column index.
            row_range (int): The number of cells in a row to update.
        Returns:
            values (list): The values of the cells in the range.
        """
        try:
            # If the sheet cannot be found, return an empty list.
            # Don't raise an error to avoid signal killing the process.
            request = (
                self.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.spreadsheet_id,
                    range=(
                        f"{sheet_name}!"
                        f"{self._column_index_to_a1(column)}{row + 1}:"
                        f"{self._column_index_to_a1(column)}{row + row_range}"
                    ),
                    majorDimension="COLUMNS",
                )
            )
            result = request.execute()
            values = result.get("values", [[]])[0]
            return values
        except HttpError:
            # Return an empty list to avoid interrupting the process.
            # This ensures that the function can handle missing or inaccessible sheets gracefully.
            print("Sheet: 未續報 not found")
            return []
