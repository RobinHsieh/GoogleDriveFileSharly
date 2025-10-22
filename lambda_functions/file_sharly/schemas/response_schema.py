from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator

from schemas.llm_schema import ReviewResult


class ShareLog(BaseModel):
    row: int
    email: str | None
    shareable_file_id_and_course_name_map: dict[str, str] = Field(default_factory=dict)
    shareable_course_name_and_if_successed_map: dict[str, bool] = None
    offset: int = -1
    review_result: ReviewResult = Field(default_factory=ReviewResult)

    @model_validator(mode='after')
    def init_success_map(cls, model: "ShareLog") -> "ShareLog":
        if model.shareable_course_name_and_if_successed_map is None:
            model.shareable_course_name_and_if_successed_map = {
                name: False
                for name in model.shareable_file_id_and_course_name_map.values()
            }
        return model


class Response(BaseModel):
    status: str
    error_type: Optional[str] = None
    shared_log: Optional[list[ShareLog]] = None
    backup_data: Optional[list[Dict[str, Any]]] = None
