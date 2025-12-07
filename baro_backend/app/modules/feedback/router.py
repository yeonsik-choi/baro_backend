# app/modules/feedback/router.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.deps import get_current_user  # 실제 경로/타입에 맞게 수정
from app.modules.auth.deps import CurrentUser       # 예시 타입

from .schemas import (
    MyPartyFeedback,
    FeedbackTarget,
    SubmitFeedbackRequest,
)
from .service import FeedbackService


router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
)


def get_feedback_service() -> FeedbackService:
    return FeedbackService()


@router.get("/my-parties", response_model=List[MyPartyFeedback])
def get_my_parties_for_feedback(
    current_user: CurrentUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
):
    """
    내가 참여한 파티 + 피드백 상태
    """
    try:
        return service.get_my_parties_for_feedback(user_id=current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/parties/{party_id}/targets", response_model=List[FeedbackTarget])
def get_feedback_targets(
    party_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
):
    """
    특정 파티에 대해 내가 평가할 대상 멤버 목록
    (본인은 제외)
    """
    try:
        return service.get_feedback_targets(party_id=party_id, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/parties/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
def submit_feedback(
    party_id: str,
    body: SubmitFeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
):
    """
    특정 파티에 대한 피드백 제출
    """
    try:
        service.submit_feedback(
            party_id=party_id,
            user_id=current_user.id,
            req=body,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
