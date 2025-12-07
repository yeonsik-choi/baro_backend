# app/modules/message/service.py
from datetime import datetime, timezone
from typing import List, Optional

from app.core.supabase import get_supabase_client
from app.modules.message.schemas import (
    Message,
    MessageRoomSummary,
    SendMessageRequest,
)


class MessageService:
    """
    파티(=채팅방) 기준 메시지 서비스

    가정한 Supabase 테이블:
      - app.party(id, title, created_at, ...)
      - app.party_member(party_id, user_id, ...)
      - app.party_message(id, room_id, sender_id, sender_name, content, created_at)
    """

    def __init__(self):
        self._client = get_supabase_client()

    # --------------------------
    # 채팅방 목록 (마지막 메시지 요약)
    # --------------------------
    def list_message_rooms(self, user_id: str) -> List[MessageRoomSummary]:
        # 1) 내가 들어가 있는 파티들 가져오기
        member_res = (
            self._client.table("app.party_member")
            .select("party_id")
            .eq("user_id", user_id)
            .execute()
        )

        if getattr(member_res, "error", None):
            raise RuntimeError(f"Failed to fetch party_member: {member_res.error}")

        party_ids = [row["party_id"] for row in member_res.data]
        if not party_ids:
            return []

        # 2) 파티 기본 정보 (방 이름용)
        party_res = (
            self._client.table("app.party")
            .select("id, title, created_at")
            .in_("id", party_ids)
            .execute()
        )
        if getattr(party_res, "error", None):
            raise RuntimeError(f"Failed to fetch party: {party_res.error}")

        party_map = {row["id"]: row for row in party_res.data}

        # 3) 각 파티별 마지막 메시지 1개씩
        summaries: List[MessageRoomSummary] = []

        for party_id in party_ids:
            party_row = party_map.get(party_id)
            if not party_row:
                # 파티가 삭제된 경우 등은 스킵
                continue

            msg_res = (
                self._client.table("app.party_message")
                .select("id, room_id, sender_id, sender_name, content, created_at")
                .eq("room_id", party_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if getattr(msg_res, "error", None):
                raise RuntimeError(
                    f"Failed to fetch last message for room {party_id}: {msg_res.error}"
                )

            if msg_res.data:
                last = msg_res.data[0]
                last_message = last["content"]
                last_message_time = self._parse_datetime(last["created_at"])
            else:
                # 아직 메시지가 없으면 파티 생성 시각이나 지금 시각을 사용
                last_message = ""
                created_at_raw: Optional[str] = party_row.get("created_at")
                if created_at_raw:
                    last_message_time = self._parse_datetime(created_at_raw)
                else:
                    last_message_time = datetime.now(timezone.utc)

            summaries.append(
                MessageRoomSummary(
                    room_id=party_id,
                    room_name=party_row.get("title", "파티"),
                    last_message=last_message,
                    last_message_time=last_message_time,
                )
            )

        # 마지막 메시지 시각 기준 내림차순 정렬
        summaries.sort(key=lambda s: s.last_message_time, reverse=True)
        return summaries

    # --------------------------
    # 특정 방의 전체 메시지
    # --------------------------
    def get_messages(self, room_id: str) -> List[Message]:
        res = (
            self._client.table("app.party_message")
            .select("id, room_id, sender_id, sender_name, content, created_at")
            .eq("room_id", room_id)
            .order("created_at", desc=False)
            .execute()
        )
        if getattr(res, "error", None):
            raise RuntimeError(f"Failed to fetch messages: {res.error}")

        return [
            Message(
                id=row["id"],
                room_id=row["room_id"],
                sender_id=row["sender_id"],
                sender_name=row["sender_name"],
                content=row["content"],
                created_at=self._parse_datetime(row["created_at"]),
            )
            for row in res.data
        ]

    # --------------------------
    # 메시지 전송
    # --------------------------
    def send_message(
        self,
        user_id: str,
        user_name: str,
        req: SendMessageRequest,
    ) -> None:
        payload = {
            "room_id": req.room_id,
            "sender_id": user_id,
            "sender_name": user_name,
            "content": req.content,
            
        }

        res = self._client.table("app.party_message").insert(payload).execute()
        if getattr(res, "error", None):
            raise RuntimeError(f"Failed to insert message: {res.error}")

    # --------------------------
    # 내부 유틸
    # --------------------------
    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """
        Supabase timestamp(UTC)를 ISO 8601로 받는다고 가정.
        예: "2025-11-20T02:30:00+00:00" 또는 "2025-11-20T02:30:00"
        """
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
           
            dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
