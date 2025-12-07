# app/modules/feedback/schemas.py
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class FeedbackStatus(str, Enum):
    AVAILABLE = "available"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class MyPartyFeedback(BaseModel):
    party_id: str
    title: str
    date: str        # "2025-12-12"
    end_at: str      # "2025-12-12T18:00:00"
    feedback_status: FeedbackStatus

    class Config:
        orm_mode = True


class FeedbackTarget(BaseModel):
    user_id: str
    nickname: str
    sportsmanship: Optional[int] = None

    class Config:
        orm_mode = True


class MemberRating(BaseModel):
    user_id: str
    rating: int


class SubmitFeedbackRequest(BaseModel):
    party_id: str
    ratings: List[MemberRating]
