from google import genai

from schemas.llm_schema import Decision, ReviewResult, ReviewResultForGeminiAPI


class ReasonReviewBot:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    """
    補課申請審核機器人，目的是防止學員濫用補課申請。
    以下爲補課理由的審核綱要：
    1. 補課理由欄位的填寫本身已降低濫用申請的可能性，請務必檢查是否有填寫內容。
    2. 理由真實性不作為審核依據，因為難以確認，所有填寫記錄均保存在資料庫，造假責任由學員負責。
    3. 不考慮理由中不必要的隱私資訊。
    4. 具體性與詳細度採從寬原則，但須避免整句話只有易複製貼上的藉口。
    5. 補課理由只需一句話完整表達即可。
    6. 判斷結果為 FAIL 表示不通過，PASS 表示通過，TBC 表示沒辦法決定通過與否，需要人工進一步確認。
    """

    def review_makeup_reason(self, reason: str) -> ReviewResult:
        prompt = f"""
你是一個補課申請審核機器人，目的是防止學員濫用補課申請，因此第二次申請補課的學員必須填寫「補課理由」。你需要從使用者提供的文字中，提取出真實敘述補課原因的部分，並忽略與請求、道歉或其他非原因敘述的語句。接著，根據下列評分標準對該理由進行分項打分，並計算出最終的 total_score，再依據此分數決定審核結果。

【基本要求】
1. 補課理由不得為空白，必須包含至少一句清楚描述原因的完整句子。

【評分標準】
請根據下列三個維度對提取出的原因進行打分，並在 explanation 中分項說明各分數的依據：

1. 理由具體性（+0 ~ +6 分）
   - +0 分：理由過於空泛，僅描述結果而無具體原因（例如：「沒看完」、「臨時有事」、「沒時間」）。
   - +6 分：理由描述非常具體，清楚指出具體原因（例如：「因為工作加班無法抽身」、「因為生病需要休息」、「期末（考試）」）。
   ※ 思考方式如：「沒看完」是結果，其具體的原因是什麼？「臨時有事」是什麼事？是加班、是生病、還是家庭因素等等？「沒時間」是因為工作、家庭、學業等等？理由具體即可，如：「段考」、「出差」，對內容細節的詳細度從寬處理。

2. 需求度／急迫性（+0 ~ +3 分）
   - +0 分：語句中未明確表達補課的迫切需求或急迫性。
   - +3 分：語句中明顯流露出急迫需要補課的意願（例如：「急需補課」、「無法彌補進度」）。
   ※ 注意：客套或附帶道歉語句不應影響急迫性評分，需聚焦於表達需求的部分。

3. 合理性（-3 ~ +2 分）
   - -3 分：理由敷衍、藉口簡短或缺乏正當性（例如：「睡過頭」、「忘記」、「玩遊戲」）。
   - +2 分：理由合理且具有說服力，能讓人理解與同理（例如：「因為生病無法觀看」、「因為工作加班耽誤補課」、「家庭緊急狀況」、「沒收到上週的連結」、「沒有收到」）。
   ※ 分析時需判斷該理由是否合理。

4. 誠懇度（+0 ~ +2 分）
   - +0 分：語句中未見禮貌或道歉表達。
   - +2 分：語句中包含禮貌、道歉或其他表達誠懇態度的語句（例如「不好意思」、「非常抱歉」、「您」）。

【最終 decision 依據 total_score】
- total_score -3 至 4 分：Decision.FAIL
- total_score 5 至 6 分：Decision.TBC
- total_score 7 至 13 分：Decision.PASS

【操作步驟】
1. 根據上述4個評分維度分別打分，並在 explanation 中分條列出每個維度的得分及評分理由。
2. 將各項分數加減計算得出 total_score，並根據最終分數給出 Decision 的結果。
3. 若補課理由為空或無法有效提取出描述原因的部分，直接判定為 Decision.FAIL，並在 explanation 中說明原因。

請根據以上指示審核每一筆補課理由，回傳的結果須包含「reason」、「total_score」、「decision」以及「explanation」4個欄位。

學生補課理由：{reason}
        """.strip()

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",  # 如有需要可根據實際情況修改模型名稱
            contents=prompt,
            config={
                "temperature": 0.05,
                "response_mime_type": "application/json",
                "response_schema": ReviewResultForGeminiAPI,
            },
        )

        api_result: ReviewResultForGeminiAPI = response.parsed

        return ReviewResult(**api_result.dict())
