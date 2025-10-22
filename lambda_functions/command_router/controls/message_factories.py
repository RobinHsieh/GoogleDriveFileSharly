from abc import ABC, abstractmethod

from entities.message_types import TextMessageResponse, FlexMessageResponse

class MessageResponseCreator(ABC):
    @staticmethod
    @abstractmethod
    def create_message_response(body: dict):
        pass

class NormalMessageResponseCreator(MessageResponseCreator):
    @staticmethod
    def create_message_response(body: dict):
        if body.get("message_type") == "text":
            return TextMessageResponse(body.get("result_message"))
        elif body.get("message_type") == "flex":
            return FlexMessageResponse("This is Flex Message", body.get("result_message"))
