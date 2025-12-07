# app/modules/message/schemas.py
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime


class MessageRoomSummary(BaseModel):
    room_id: str
    room_name: str
    last_message: str
    last_message_time: datetime


class SendMessageRequest(BaseModel):
    room_id: str
    content: str
