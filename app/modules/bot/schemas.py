# app/modules/bot/schemas.py

from __future__ import annotations

from pydantic import BaseModel
from typing import List, Literal, Optional

# -----------------------------
# 기존 챗봇 엔진용 스키마
# -----------------------------

class ChatRequest(BaseModel):
    """
    process_bot_message 에서 req.xxx 로 접근하는 필드를 모두 정의한 모델
    """

    # (필수) 사용자가 실제로 보낸 메시지
    message: str
    
    thread_id: str | None = None

    # (1) 기본 정보
    nickname: str | None = None
    gender: str | None = None
    birth_date: str | None = None   # "YYYY-MM-DD" 형식
    age: int | None = None

    # (2) 신체 정보
    height: float | None = None        # cm
    weight: float | None = None        # kg
    muscle_mass: float | None = None   # kg

    # (3) 운동 성향
    skill_level: str | None = None
    favorite_sports: List[str] | None = None

    # (4) 위치 정보
    latitude: float | None = None
    longitude: float | None = None

    # (5) 기타 컨텍스트
    user_id: str | None = None
    room_id: str | None = None

class ChatResponse(BaseModel):
    """
    기존 /chatbot/message 에서 쓰던 응답 모델
    """
    answer: str


# -----------------------------
# 안드로이드용 DTO 대응 스키마
# -----------------------------

class ChatRoomSummary(BaseModel):
    """
    안드로이드 ChatRoomSummaryDto 에 대응
    """
    id: str
    title: str
    lastMessage: str
    createdAt: int  # epoch millis


class ChatMessage(BaseModel):
    """
    안드로이드 ChatMessageDto 에 대응
    """
    id: str
    text: str
    sender: Literal["USER", "BOT"]
    timestamp: int  # epoch millis


class BotRequest(BaseModel):
    """
    안드로이드 BotRequestDto 에 대응
    """
    text: str
    
   
    thread_id: str | None = None 


class BotResponse(BaseModel):
    """
    안드로이드 BotResponseDto 에 대응
    """
    messages: List[ChatMessage]