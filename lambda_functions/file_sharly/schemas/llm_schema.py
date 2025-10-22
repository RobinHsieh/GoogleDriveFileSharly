from enum import Enum
from pydantic import BaseModel


class Decision(str, Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    TBC = "ToBeConfirmed"


class ReviewResult(BaseModel):
    reason: str = "空白。"
    total_score: int = 0
    decision: Decision = Decision.FAIL
    explanation: str = "尚未初始化。"


class ReviewResultForGeminiAPI(BaseModel):
    """
    Default value is not supported in the response schema for the Gemini API
    """
    reason: str
    total_score: int
    decision: Decision
    explanation: str
