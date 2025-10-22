from abc import ABC, abstractmethod
from linebot.models import TextSendMessage, FlexSendMessage, ImageSendMessage

class MessageResponse(ABC):
    
    @abstractmethod
    def create_line_message(self):
        pass

class TextMessageResponse(MessageResponse):
    
    def __init__(self, text):
        self.text = text
    
    def create_line_message(self):
        return TextSendMessage(text=self.text)

class FlexMessageResponse(MessageResponse):
    
    def __init__(self, alt_text, contents):
        self.alt_text = alt_text
        self.contents = contents
    
    def create_line_message(self):
        return FlexSendMessage(alt_text=self.alt_text, contents=self.contents)

class ImageMessageResponse(MessageResponse):
    
    def __init__(self, original_content_url, preview_image_url):
        self.original_content_url = original_content_url
        self.preview_image_url = preview_image_url
    
    def create_line_message(self):
        return ImageSendMessage(
            original_content_url=self.original_content_url,
            preview_image_url=self.preview_image_url
        )
