# app/modules/message/router.py
from typing import List

from fastapi import APIRouter, Depends, status

from app.modules.message.schemas import (
    Message,
    MessageRoomSummary,
    SendMessageRequest,
)
from app.modules.message.service import MessageService

# 실제 프로젝트의 auth 모듈에 맞게 import 수정
from app.modules.auth.deps import get_current_user_id as get_current_user


router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)


def get_message_service() -> MessageService:
    return MessageService()


@router.get(
    "/rooms",
    response_model=List[MessageRoomSummary],
)
def get_message_rooms(
    current_user=Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    """
    현재 로그인한 사용자가 속한 파티(=채팅방)의 마지막 메시지 목록
    Android: GET /messages/rooms
    """
    return service.list_message_rooms(user_id=current_user.id)


@router.get(
    "/{room_id}",
    response_model=List[Message],
)
def get_messages(
    room_id: str,
    current_user=Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    """
    특정 채팅방의 전체 메시지
    Android: GET /messages/{roomId}
    """
    
    return service.get_messages(room_id=room_id)


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
def send_message(
    req: SendMessageRequest,
    current_user=Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    """
    메시지 전송
    Android: POST /messages
    body: { "room_id": "...", "content": "..." }
    """
    
    user_name = getattr(current_user, "name", None) or getattr(
        current_user, "nickname", "익명"
    )
    service.send_message(
        user_id=current_user.id,
        user_name=user_name,
        req=req,
    )
