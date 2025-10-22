import os
import logging
from pandas import DataFrame
from abc import ABC, abstractmethod

from interfaces.google_sheet_client import GoogleSheetClient
from interfaces.llm_client import ReasonReviewBot
from schemas.llm_schema import Decision, ReviewResult
from schemas.state_schema import CellState, UserState

logger = logging.getLogger("file_sharly")


class ViewLimitStrategy(ABC):
    """
    An abstract class for the view limit strategy.
    """

    @abstractmethod
    def get_cell_state(red: int, green: int, blue: int) -> CellState:
        """
        Get the cell state based on the cell color.
        Args:
            red (int): The red value.
            green (int): The green value.
            blue (int): The blue value.
        Returns:
            if_view_limit_near (bool): If the view limit is near.
            if_view_limit_reached (bool): If the view limit reached.
        """
        pass


class TwiceQuota(ViewLimitStrategy):
    """
    A class for the view limit strategy of twice quota.
    """

    @staticmethod
    def get_cell_state(red: int, green: int, blue: int) -> CellState:
        # if cell's color is white
        if (red, green, blue) == (1, 1, 1) or (red, green, blue) == (0, 0, 0):
            if_view_limit_near = False
            if_view_limit_reached = False

        # if cell's color is yellow
        elif (red, green, blue) == (1, 1, 0):
            if_view_limit_near = True
            if_view_limit_reached = False

        # if cell's color is green
        elif (red, green, blue) == (0, 1, 0):
            if_view_limit_near = False
            if_view_limit_reached = True

        # if cell's color is blue
        else:
            if_view_limit_near = False
            if_view_limit_reached = True

        return CellState(
            if_view_limit_near=if_view_limit_near,
            if_view_limit_reached=if_view_limit_reached,
        )


class ThreeTimesQuota(ViewLimitStrategy):
    """
    A class for the view limit strategy of three times quota.
    """

    @staticmethod
    def get_cell_state(red: int, green: int, blue: int) -> CellState:
        # if cell's color is white
        if (red, green, blue) == (1, 1, 1) or (red, green, blue) == (0, 0, 0):
            if_view_limit_near = False
            if_view_limit_reached = False

        # if cell's color is yellow
        elif (red, green, blue) == (1, 1, 0):
            if_view_limit_near = False
            if_view_limit_reached = False

        # if cell's color is green
        elif (red, green, blue) == (0, 1, 0):
            if_view_limit_near = True
            if_view_limit_reached = False

        # if cell's color is blue
        else:
            if_view_limit_near = False
            if_view_limit_reached = True

        return CellState(
            if_view_limit_near=if_view_limit_near,
            if_view_limit_reached=if_view_limit_reached,
        )


class ReviewReasonStrategy(ABC):
    """
    An abstract class for the review reason strategy.
    """

    @abstractmethod
    def review_reason_in_cell() -> ReviewResult:
        pass


class ReviewReasonByLLM(ReviewReasonStrategy):
    """
    A class for the review reason strategy by LLM.
    """

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    reason_review_bot = ReasonReviewBot(api_key=gemini_api_key)

    @classmethod
    def review_reason_in_cell(cls, row: int, data_frame: DataFrame) -> ReviewResult:
        reason = data_frame.at[row, "第二次申請補課原因"]
        reason_response = cls.reason_review_bot.review_makeup_reason(reason)
        logger.info(
            f"{reason_response.reason}\n{reason_response.total_score} {reason_response.decision}\n{reason_response.explanation}"
        )  # print Log
        return reason_response


class DoNotReviewReason(ReviewReasonStrategy):
    """
    A class for the review reason strategy of not reviewing.
    """

    @classmethod
    def review_reason_in_cell(cls, row: int, data_frame: DataFrame) -> ReviewResult:
        return ReviewResult(
            reason="不需要。",
            total_score=11,
            decision=Decision.PASS,
            explanation="無條件通過。",
        )


class PropertyAndStateManager:
    """
    A class to manage cell colors in Google Sheets.
    Stateful class.
    """

    def __init__(self, **kwargs):
        self.view_limit_strategy = kwargs.get("view_limit_strategy", None)
        self.review_reason_strategy = kwargs.get("review_reason_strategy", None)

    def set_view_limit_strategy(self, view_limit_strategy: ViewLimitStrategy):
        self.view_limit_strategy = view_limit_strategy

    def set_review_reason_strategy(self, review_reason_strategy: ReviewReasonStrategy):
        self.review_reason_strategy = review_reason_strategy

    def get_cell_state(self, red: int, green: int, blue: int) -> CellState:
        return self.view_limit_strategy.get_cell_state(red, green, blue)

    def review_reason_in_cell(self, row: int, data_frame: DataFrame) -> ReviewResult:
        return self.review_reason_strategy.review_reason_in_cell(row, data_frame)

    @staticmethod
    def update_cell_properties(
        red: int,  # color
        green: int,  # color
        blue: int,  # color
        cell_state: CellState,
        user_state: UserState,
        sheet_client: GoogleSheetClient,
        row: int,  # cell
        date_column_index: int,  # cell
    ):
        """
        Update the cell properties based on the cell color.
        Args:
            red (int): The red value.
            green (int): The green value.
            blue (int): The blue value.
            cell_state (CellState): The state of the cell.
            user_state (UserState): The state of the user.
            sheet_client (GoogleSheetClient): The Google Sheet client.
            row (int): The row index of the cell.
            date_column_index (int): The column index of the date.
        """
        if PropertyAndStateManager._should_update(cell_state, user_state):
            # if cell's color is white
            if (red, green, blue) == (1, 1, 1) or (red, green, blue) == (0, 0, 0):
                red, green, blue = 1, 1, 0

            # if cell's color is yellow
            elif (red, green, blue) == (1, 1, 0):
                red, green, blue = 0, 1, 0

            # if cell's color is green
            elif (red, green, blue) == (0, 1, 0):
                red, green, blue = 0, 1, 1

            updated_red, updated_green, updated_blue = red, green, blue
            sheet_client.append_write_cells_color_request(
                row + 1,
                date_column_index,
                1,
                updated_red,
                updated_green,
                updated_blue,
            )

    @staticmethod
    def get_updated_user_state(
        file_id_index: int,
        file_id_list: list[dict],
        cell_state: CellState,
        user_state: UserState,
    ) -> UserState:
        """
        Update the UserState based on the row of cells color.
        """

        if PropertyAndStateManager._should_update(cell_state, user_state):
            user_state.shareable_file_id_and_course_name_map[
                file_id_list[file_id_index].get("FileID")
            ] = file_id_list[file_id_index].get("SK")
            user_state.offset += 2
            if cell_state.if_view_limit_near and user_state.review_result.decision in [
                Decision.PASS,
                Decision.TBC,
            ]:
                user_state.view_limit_near_course_name_list.append(
                    file_id_list[file_id_index].get("SK")
                )

        return user_state

    @staticmethod
    def _should_update(
        cell_state: CellState,
        user_state: UserState,
    ) -> bool:
        """
        Check if the cell state and user state need to be updated.
        """
        if cell_state.if_view_limit_reached:
            return False
        elif cell_state.if_view_limit_near and user_state.review_result.decision in [
            Decision.FAIL
        ]:
            return False
        else:
            return True
