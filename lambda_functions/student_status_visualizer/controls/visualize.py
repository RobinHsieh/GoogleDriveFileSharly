import re
import json
from interfaces.googe_sheet_client import GoogleSheetClient


def leave_status(sheet_client: GoogleSheetClient, target_date: str):
    # 設定淺紅色
    return status(sheet_client, target_date, 1, 0.5, 0.5, "請假")


def late_arrival_status(sheet_client: GoogleSheetClient, target_date: str):
    # 設定淺藍色
    return status(sheet_client, target_date, 0.5, 0.5, 1, "晚到")


def status(sheet_client: GoogleSheetClient, target_date: str, red, green, blue, status: str):

    # ======================== 讀取 請假/晚到 ========================
    try:
        sheet_data_frame = sheet_client.get_sheet_as_data_frame("請假/晚到")
    except Exception as e:
        result_message = f"讀取請假/晚到工作表失敗: {e}"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }

    # 輸出欄位名稱確認（第一列已轉成欄位名稱）
    print("工作表欄位：", list(sheet_data_frame.columns))

    # 篩選指定日期的請假記錄
    if target_date not in sheet_data_frame.columns:
        result_message = f"找不到日期欄位為 {target_date} 的課程"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }

    # 選出指定日期中填寫 "請假" 或 "晚到" 的記錄
    absent_mask = sheet_data_frame[target_date].isin([status])
    absent_data_frame = sheet_data_frame[absent_mask]

    if absent_data_frame.empty:
        result_message = f"{target_date} 沒有{status}的記錄。"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }
    else:
        print(f"找到 {len(absent_data_frame)} 筆 {target_date} 的{status}記錄。")

    # 取得對應的座位表儲存格（A1 notation），假設欄位名稱為 "座位表儲存格"
    if "座位表儲存格" not in absent_data_frame.columns:
        result_message = "工作表中沒有欄位 '座位表儲存格'。"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }
    
    absent_seat_cell_list = absent_data_frame["座位表儲存格"].dropna().tolist()
    absent_seat_cell_list = [x for x in absent_seat_cell_list if x != "#VALUE!"]
    print("將更新座位位置：", absent_seat_cell_list)

    # 將每個 A1 notation 轉換為 row 與 column index，並加入更新請求
    for absent_seat_cell in absent_seat_cell_list:
        try:
            print(f"處理座位 {absent_seat_cell}...")  # Debugging
            row_idx, column_idx = convert_a1_to_indices(absent_seat_cell)
            # 此處設定背景，設定值可調整 (red=1, green=0, blue=0 為純紅)
            sheet_client.append_write_cells_color_request(
                row=row_idx,
                column=column_idx,
                row_range=1,  # 單一儲存格
                red=red,
                green=green,
                blue=blue,
                sheet_name="座位表",
            )
            print(
                f"準備將座位 {absent_seat_cell}（row {row_idx}, column {column_idx}）標記。"
            )
        except ValueError as ve:
            print(ve)
    
    # ======================== 讀取 同步直播 ========================
    try:
        sheet_data_frame = sheet_client.get_sheet_as_data_frame("同步直播")
    except Exception as e:
        result_message = f"讀取同步直播工作表失敗: {e}"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }

    # 輸出欄位名稱確認（第一列已轉成欄位名稱）
    print("工作表欄位：", list(sheet_data_frame.columns))

    # 篩選指定日期的請假記錄
    if target_date not in sheet_data_frame.columns:
        result_message = f"找不到日期欄位為 {target_date} 的課程"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }

    # 選出申請類別中填寫 "臨時請假" 或 "晚到" 、並且指定日期填寫 "V" 的記錄
    if status == "請假":
        status = "臨時請假"
    absent_mask = sheet_data_frame["申請類別"].isin([status]) & sheet_data_frame[target_date].isin(["V"])
    absent_data_frame = sheet_data_frame[absent_mask]

    if absent_data_frame.empty:
        result_message = f"{target_date} 沒有{status}的記錄。"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }
    else:
        print(f"找到 {len(absent_data_frame)} 筆 {target_date} 的{status}記錄。")

    # 取得對應的座位表儲存格（A1 notation），假設欄位名稱為 "座位表儲存格"
    if "座位表儲存格" not in absent_data_frame.columns:
        result_message = "工作表中沒有欄位 '座位表儲存格'。"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }

    absent_seat_cell_list = absent_data_frame["座位表儲存格"].dropna().tolist()
    absent_seat_cell_list = [x for x in absent_seat_cell_list if x != "#VALUE!"]
    print("將更新座位位置：", absent_seat_cell_list)

    # 將每個 A1 notation 轉換為 row 與 column index，並加入更新請求
    for absent_seat_cell in absent_seat_cell_list:
        try:
            print(f"處理座位 {absent_seat_cell}...")  # Debugging
            row_idx, column_idx = convert_a1_to_indices(absent_seat_cell)
            # 此處設定背景，設定值可調整 (red=1, green=0, blue=0 為純紅)
            sheet_client.append_write_cells_color_request(
                row=row_idx,
                column=column_idx,
                row_range=1,  # 單一儲存格
                red=red,
                green=green,
                blue=blue,
                sheet_name="座位表",
            )
            print(
                f"準備將座位 {absent_seat_cell}（row {row_idx}, column {column_idx}）標記。"
            )
        except ValueError as ve:
            print(ve)



    # ======================== 執行所有格式更新請求 ========================
    try:
        sheet_client.execute_write_cells_color_requests()
        result_message = f"當日{target_date}課程中\n所有{status}者對應座位已成功標記！"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }
    except Exception as e:
        result_message = f"更新儲存格顏色失敗：{e}"
        return {
            "statusCode": 200,
            "body": {"message_type": "text", "result_message": result_message},
        }


def recital_selection(sheet_client: GoogleSheetClient, target_date):
    result_message = "背書顯示功能尚未實作，敬請期待><!"
    return {
        "statusCode": 200,
        "body": {"message_type": "text", "result_message": result_message},
    }


def convert_a1_to_indices(a1_notation):
    """
    將 A1 notation 轉換為 0-index 的 (row_index, column_index)
    例如 "F9" 轉換成 (8, 5)
    """
    match = re.match(r"([A-Za-z]+)(\d+)", a1_notation)
    if not match:
        raise ValueError(f"無法解析的 A1 notation: {a1_notation}")
    letters, digits = match.groups()
    column = 0
    for char in letters.upper():
        column = column * 26 + (ord(char) - ord("A") + 1)
    col_index = column - 1
    row_index = int(digits) - 1
    return row_index, col_index
