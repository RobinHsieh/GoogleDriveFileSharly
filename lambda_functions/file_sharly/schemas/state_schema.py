from pydantic import BaseModel, Field

from schemas.llm_schema import ReviewResult


class CellState(BaseModel):
    if_view_limit_near: bool
    if_view_limit_reached: bool


class UserState(BaseModel):
    offset: int = -1
    review_result: ReviewResult = Field(default_factory=ReviewResult)
    shareable_file_id_and_course_name_map: dict[str, str] = Field(default_factory=dict)
    view_limit_near_course_name_list: list[str] = Field(default_factory=list)
