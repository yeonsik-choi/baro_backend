# app/modules/party/router.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from .schemas import CreatePartyRequest, Party
from .service import PartyService

# 기존 auth 모듈에 있는 의존성 가정
from app.modules.auth.deps import get_current_user_id

router = APIRouter(
    prefix="/party",
    tags=["party"],
)


def get_party_service() -> PartyService:
    # 나중에 DI 컨테이너 쓰면 여기만 바꾸면 됨
    return PartyService()


# GET /party  -> PartyApi.getPartyList()
@router.get("", response_model=List[Party])
async def get_party_list(
    service: PartyService = Depends(get_party_service),
    user_id: str = Depends(get_current_user_id),   # 없으면 Optional[str]
):
    parties = service.get_party_list(user_id=user_id)
    # Party 모델은 alias 설정해놔서 JSON 키가 partyId, startTime 등으로 나갈 것
    return parties


# GET /party/{partyId}  -> getPartyDetail()
@router.get("/{party_id}", response_model=Party)
async def get_party_detail(
    party_id: str,
    service: PartyService = Depends(get_party_service),
    user_id: str = Depends(get_current_user_id),
):
    party = service.get_party_detail(party_id=party_id, user_id=user_id)
    if not party:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Party not found")
    return party


# POST /party  -> createParty()
@router.post("", response_model=Party, status_code=status.HTTP_201_CREATED)
async def create_party(
    req: CreatePartyRequest,
    service: PartyService = Depends(get_party_service),
    user_id: str = Depends(get_current_user_id),
):
    party = service.create_party(user_id=user_id, req=req)
    return party


# POST /party/{partyId}/join
@router.post("/{party_id}/join", response_model=Party)
async def join_party(
    party_id: str,
    service: PartyService = Depends(get_party_service),
    user_id: str = Depends(get_current_user_id),
):
    party = service.join_party(party_id=party_id, user_id=user_id)
    return party


# POST /party/{partyId}/leave
@router.post("/{party_id}/leave", response_model=Party)
async def leave_party(
    party_id: str,
    service: PartyService = Depends(get_party_service),
    user_id: str = Depends(get_current_user_id),
):
    party = service.leave_party(party_id=party_id, user_id=user_id)
    return party