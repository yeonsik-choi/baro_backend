# app/modules/bot/router.py

from __future__ import annotations

import logging
import time
import uuid
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from app.modules.auth.deps import get_current_auth_user
from app.modules.auth.schemas import AuthUser


from app.core.supabase import supabase_client

# 안드로이드용 스키마
from app.modules.bot.schemas import (
    BotRequest,
    BotResponse,
    ChatMessage,
    ChatRoomSummary,
)

# 기존 챗봇 엔진용 스키마/서비스
from app.modules.bot.schemas import ChatRequest as AgentChatRequest
from app.modules.bot.service import process_bot_message

router = APIRouter(prefix="/bot", tags=["Bot"])
logger = logging.getLogger(__name__)


@router.get("/rooms", response_model=List[ChatRoomSummary])
def get_chat_rooms() -> List[ChatRoomSummary]:
    try:
        # DB에서 세션 목록 조회
        response = supabase_client.schema("app").table("chat_session")\
            .select("*").order("created_at", desc=True).execute()
        
        rooms = []
        for item in response.data:
            
            created_at_val = item.get("created_at")
            created_at_ms = 0
            
            if isinstance(created_at_val, str):
                try:
                    dt = datetime.fromisoformat(created_at_val)
                    created_at_ms = int(dt.timestamp() * 1000)
                except:
                    created_at_ms = 0
            elif isinstance(created_at_val, (int, float)):
                created_at_ms = int(created_at_val)

            rooms.append(ChatRoomSummary(
                id=item["id"],
                title=item.get("title", f"채팅방 {item['id'][:8]}"),
                lastMessage=item.get("last_message", ""),
                createdAt=created_at_ms,
            ))
        return rooms
    except Exception as e:
        logger.error(f"Failed to fetch rooms: {e}")
        return []


@router.get("/rooms/{room_id}/messages", response_model=List[ChatMessage])
def get_messages(room_id: str) -> List[ChatMessage]:
    try:
        # DB에서 메시지 조회
        response = supabase_client.schema("app").table("chat_messages")\
            .select("*").eq("session_id", room_id).order("timestamp", desc=False).execute()
        
        messages = []
        for item in response.data:
            
            db_sender = item.get("sender", "user")
            if db_sender == "assistant":
                app_sender = "BOT"
            else:
                app_sender = "USER"

            messages.append(ChatMessage(
                id=str(item.get("id", uuid.uuid4())),
                text=item["text"],
                sender=app_sender,
                timestamp=item["timestamp"]
            ))
        return messages
    except Exception as e:
        logger.error(f"Failed to fetch messages for room {room_id}: {e}")
        return []


@router.post("/rooms/{room_id}/messages", response_model=BotResponse)
def send_message(
    room_id: str, 
    req: BotRequest,
    user: AuthUser = Depends(get_current_auth_user)
) -> BotResponse:
    logger.info("send_message called: room_id=%s, text=%s", room_id, req.text)

    # 사용자 프로필 정보를 포함하여 ChatRequest 생성
    agent_req = AgentChatRequest(
        message=req.text,
        thread_id=room_id,
        room_id=room_id,
        # --- 사용자 정보 매핑 ---
        user_id=str(user.id),
        nickname=user.nickname,
        gender=user.gender,
        age=user.age,                 # AuthUser.age -> ChatRequest.age
        height=user.height_cm,        # AuthUser.height_cm -> ChatRequest.height
        weight=user.weight_kg,        # AuthUser.weight_kg -> ChatRequest.weight
        skill_level=user.level,       # AuthUser.level -> ChatRequest.skill_level
        favorite_sports=user.preferred_sports, # AuthUser.preferred_sports -> ChatRequest.favorite_sports
        latitude=user.latitude,
        longitude=user.longitude
    )
    
    # 유저 메시지 DB 저장 -> 랭체인 실행 -> 봇 응답 DB 저장 수행
    agent_answer = process_bot_message(agent_req)

    # 프론트엔드 응답용 객체 생성
    bot_msg = ChatMessage(
        id=str(uuid.uuid4()),
        text=agent_answer,
        sender="BOT",
        timestamp=int(time.time() * 1000),
    )

    return BotResponse(messages=[bot_msg])