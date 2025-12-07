# app/modules/feedback/service.py
from typing import List

from .repository import FeedbackRepository
from .schemas import (
    MyPartyFeedback,
    FeedbackTarget,
    MemberRating,
    SubmitFeedbackRequest,
)


class FeedbackService:
    def __init__(self, repo: FeedbackRepository | None = None) -> None:
        self.repo = repo or FeedbackRepository()

    def get_my_parties_for_feedback(self, user_id: str) -> List[MyPartyFeedback]:
        return self.repo.get_my_parties(user_id)

    def get_feedback_targets(self, party_id: str, user_id: str) -> List[FeedbackTarget]:
        return self.repo.get_feedback_targets(party_id, user_id)

    def submit_feedback(
        self,
        party_id: str,
        user_id: str,
        req: SubmitFeedbackRequest,
    ) -> None:
        # path 의 party_id 와 body 의 party_id 가 다르면 에러
        if req.party_id and req.party_id != party_id:
            raise ValueError("party_id in path and body are different.")

        ratings: List[MemberRating] = req.ratings
        self.repo.submit_feedback(party_id=party_id, rater_id=user_id, ratings=ratings)
