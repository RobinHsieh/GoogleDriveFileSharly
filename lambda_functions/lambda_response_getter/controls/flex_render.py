def create_flex_message(lambda_response_list):
    """
    將 Lambda 響應列表轉換為 Line Flex Message 格式
    """
    bubbles = []

    for lambda_response in lambda_response_list:
        course_batch_id = lambda_response.get("CourseBatchId", "未知課程批次")
        batch_number = lambda_response.get("BATCH", "未知梯次")
        week_day = lambda_response.get("WEEK_DAY", "未知星期")
        date = lambda_response.get("Date", "未知日期")
        response = lambda_response.get("Response", {})

        if response.get("status") == "error":
            bubble = create_error_bubble(
                course_batch_id, batch_number, week_day, date, response
            )
            bubbles.append(bubble)
        elif response.get("status") == "success":
            bubble = create_success_bubble(
                course_batch_id, batch_number, week_day, date, response
            )
            if bubble:  # 只有在實際有用戶資料時才添加
                bubbles.append(bubble)

    # 如果 bubbles 是空的，添加一個"尚未有發送紀錄"的 bubble
    if not bubbles:
        bubbles.append(create_empty_bubble())

    # 創建 Carousel 容器
    flex_message = {"type": "carousel", "contents": bubbles}

    return flex_message


def create_error_bubble(course_batch_id, batch_number, week_day, date, response):
    """
    創建錯誤信息的 Bubble
    """
    error_type = response.get("error_type", "未知錯誤")

    # 創建錯誤內容區塊
    error_contents = create_error_box(error_type)

    # 創建用戶資料區塊
    users_contents = create_users_contents(response.get("shared_log", []))

    # 創建錯誤信息的 Bubble
    bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"{course_batch_id}  {batch_number}  {week_day}  {date}",
                    "color": "#FF0000",
                    "weight": "bold",
                    "align": "center",
                    "size": "lg",
                    "wrap": True,  # 確保標題可以換行
                }
            ],
            "backgroundColor": "#FFE4E1",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [error_contents]
            + users_contents,  # 先添加錯誤內容，再添加用戶內容
            "spacing": "sm",
        },
        "size": "mega",  # 使用較大的氣泡尺寸，以防內容過多
    }

    return bubble


def create_success_bubble(course_batch_id, batch_number, week_day, date, response):
    """
    創建成功信息的 Bubble
    """
    shared_log = response.get("shared_log", [])

    # 創建用戶資料區塊
    user_contents = create_users_contents(shared_log)

    # 只有在有用戶資料時才創建 bubble
    if user_contents:
        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{course_batch_id}  {batch_number}  {week_day}  {date}",
                        "weight": "bold",
                        "color": "#1DB446",
                        "align": "center",
                        "size": "lg",
                        "wrap": True,  # 確保標題可以換行
                    }
                ],
                "backgroundColor": "#F2FFE6",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": user_contents,
                "spacing": "sm",
            },
            "size": "mega",  # 使用較大的氣泡尺寸，以防內容過多
        }
        return bubble

    return None


def create_error_box(error_type):
    """
    創建錯誤內容區塊
    """
    return {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": error_type,
                "weight": "bold",
                "size": "md",
                "align": "center",
                "wrap": True,
            }
        ],
        "spacing": "md",
        "backgroundColor": "#FFE4E1",
        "cornerRadius": "md",
        "paddingAll": "md",
        "margin": "md",
    }


def create_empty_bubble():
    """
    創建"尚未有發送紀錄"的 bubble
    """
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "尚未有發送紀錄",
                    "weight": "bold",
                    "size": "md",
                    "align": "center",
                    "color": "#888888",
                }
            ],
            "justifyContent": "center",
            "alignItems": "center",
            "paddingAll": "xl",
        },
    }


def create_users_contents(shared_log):
    """
    為用戶列表創建內容區塊
    """
    user_contents = []

    for user in shared_log:
        if user.get("email") is None:
            continue
        if user.get("offset") == -1 and (
            user.get("review_result", {}).get("explanation") == "尚未初始化。"
        ):
            continue

        # 創建用戶容器
        user_container = create_user_box(user)

        # 添加分隔線
        separator = {"type": "separator", "margin": "md"}

        # 添加用戶容器和分隔線到內容列表
        user_contents.append(user_container)
        user_contents.append(separator)

    # 如果有用戶資料，移除最後一個分隔線
    if user_contents:
        user_contents.pop()

    return user_contents


def create_user_box(user):
    """
    創建單個用戶的容器
    """
    # 用戶頂部資訊區
    top_info_row = create_user_top_info(user)

    # 用戶基本資料區塊
    user_info = create_user_info(user)

    # 課程列表顯示為表格
    course_table = create_course_table(user)

    # 用戶資訊容器
    user_container = {
        "type": "box",
        "layout": "vertical",
        "contents": [
            top_info_row,  # 行號和開放天數在同一行
            user_info,  # 用戶 email
            course_table,  # 課程列表
        ],
        "backgroundColor": "#F5F5F5",
        "cornerRadius": "md",
        "paddingAll": "md",
        "margin": "md",
    }

    # 檢查是否有評審結果
    review_result = user.get("review_result", {})
    if review_result.get("explanation") != "尚未初始化。":
        # 添加評審結果到用戶容器
        review_info = create_review_info(review_result)
        user_container["contents"].append(review_info)

    return user_container


def create_user_top_info(user):
    """
    創建用戶頂部資訊區
    """
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{user.get('row', '')}",
                        "size": "xs",
                        "color": "#FFFFFF",
                        "weight": "bold",
                        "align": "center",
                    }
                ],
                "backgroundColor": "#6699CC",
                "cornerRadius": "sm",
                "paddingAll": "xs",
                "width": "30px",
                "height": "20px",
            },
            {
                "type": "text",
                "text": f"開放天數: {user.get('offset', -1) + 1}",
                "size": "xs",
                "color": "#888888",
                "margin": "sm",
                "flex": 5,
            },
        ],
        "margin": "xs",
    }


def create_user_info(user):
    """
    創建用戶基本資料區塊
    """
    return {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": user.get("email", ""),
                "size": "sm",
                "weight": "bold",
                "wrap": True,
                "margin": "xs",
            }
        ],
    }


def create_course_table(user):
    """
    創建課程表格
    """
    shareable_course_name_and_if_successed_map = user.get(
        "shareable_course_name_and_if_successed_map", {}
    )
    course_table_rows = []

    if shareable_course_name_and_if_successed_map:
        # 表格標題
        course_table_rows.append(create_table_header("寄出課程"))

        # 添加每個課程為表格行
        for course, if_successed in shareable_course_name_and_if_successed_map.items():
            text_color = "#FF0000" if not if_successed else "#555555"  # 紅色或灰色
            text_decoration = (
                "line-through" if not if_successed else "none"
            )  # 有刪除線或無

            course_row = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "• " + course,
                        "size": "xs",
                        "color": text_color,
                        "wrap": True,  # 確保課程名稱可以換行
                        "decoration": text_decoration,  # 添加刪除線屬性
                    }
                ],
                "paddingAll": "sm",
            }
            course_table_rows.append(course_row)

    # 組合課程表格
    return {
        "type": "box",
        "layout": "vertical",
        "contents": course_table_rows,
        "margin": "md",
        "cornerRadius": "sm",
        "borderWidth": "1px",
        "borderColor": "#DDDDDD",
    }


def create_review_info(review_result):
    """
    創建評審結果區塊
    """
    return {
        "type": "box",
        "layout": "vertical",
        "contents": [
            create_table_header("原因"),
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": review_result.get("reason", ""),
                        "size": "xs",
                        "wrap": True,
                    }
                ],
                "paddingAll": "sm",
            },
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "總分",
                        "size": "xs",
                        "color": "#555555",
                        "flex": 1,
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": "決定",
                        "size": "xs",
                        "color": "#555555",
                        "flex": 1,
                        "weight": "bold",
                    },
                ],
                "backgroundColor": "#EEEEEE",
                "paddingAll": "sm",
            },
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{review_result.get('total_score', '')}",
                        "size": "sm",
                        "color": "#1DB446",
                        "weight": "bold",
                        "flex": 1,
                    },
                    {
                        "type": "text",
                        "text": f"{review_result.get('decision', '')}",
                        "size": "sm",
                        "color": review_result.get("decision") == "通過"
                        and "#1DB446"
                        or "#FF0000",
                        "weight": "bold",
                        "flex": 1,
                    },
                ],
                "paddingAll": "sm",
            },
            create_table_header("說明"),
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": review_result.get("explanation", ""),
                        "size": "xs",
                        "wrap": True,  # 確保說明可以換行
                    }
                ],
                "paddingAll": "sm",
            },
        ],
        "margin": "lg",
        "cornerRadius": "sm",
        "borderWidth": "1px",
        "borderColor": "#DDDDDD",
    }


def create_table_header(text):
    """
    創建表格標題行
    """
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {
                "type": "text",
                "text": text,
                "size": "xs",
                "color": "#555555",
                "weight": "bold",
            }
        ],
        "backgroundColor": "#EEEEEE",
        "paddingAll": "sm",
    }
