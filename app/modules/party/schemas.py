# app/modules/party/schemas.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreatePartyRequest(BaseModel):
    # 안드는 start_time, end_time, place_lat, place_lng 라는 JSON 키를 보냄
    title: str
    sport: str
    place: str
    description: str
    date: str
    start_time: str
    end_time: str
    capacity: int
    place_lat: Optional[float] = None
    place_lng: Optional[float] = None


class PartyMember(BaseModel):
    party_id: str
    user_id: str
    nickname: str
    role: str              # "host" / "member"
    status: str            # "joined" / "left" / "kicked"
    joined_at: str
    sportsmanship: Optional[int] = None


class Party(BaseModel):
    # 여기서는 파이썬에선 snake_case 쓰고, JSON은 안드쪽 camelCase에 맞게 alias를 줘도 되고
    # 귀찮으면 필드 이름 자체를 camelCase로 써도 됨.
    party_id: str = Field(alias="partyId")
    title: str
    sport: str
    place: str
    description: str
    date: str
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    capacity: int
    current: int
    host_id: str = Field(alias="hostId")
    status: str
    members: List[PartyMember] = []
    is_joined: bool = Field(alias="isJoined")
    created_at: str = Field(alias="createdAt")
    place_lat: Optional[float] = Field(default=None, alias="placeLat")
    place_lng: Optional[float] = Field(default=None, alias="placeLng")

    class Config:
        populate_by_name = True   # 내부에서 party_id로 세팅해도 응답 JSON은 partyId로 나감
        orm_mode = True           # DB row -> 모델 변환 편하게
