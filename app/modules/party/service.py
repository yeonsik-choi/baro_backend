# app/modules/party/service.py
from typing import List, Optional

from .repository import PartyRepository
from .schemas import CreatePartyRequest, Party


class PartyService:
    def __init__(self, repo: PartyRepository | None = None):
        self.repo = repo or PartyRepository()

    def get_party_list(self, user_id: Optional[str]) -> List[Party]:
        return self.repo.list_parties(user_id=user_id)

    def get_party_detail(self, party_id: str, user_id: Optional[str]) -> Party:
        return self.repo.get_party(party_id=party_id, user_id=user_id)

    def create_party(self, user_id: str, req: CreatePartyRequest) -> Party:
        # 여기서 capacity 체크, 날짜/시간 검증 같은 것 넣을 수 있음
        return self.repo.create_party(user_id=user_id, req=req)

    def join_party(self, party_id: str, user_id: str) -> Party:
        # ex) 이미 조인했으면 에러, capacity 초과면 에러
        return self.repo.join_party(party_id=party_id, user_id=user_id)

    def leave_party(self, party_id: str, user_id: str) -> Party:
        # ex) host는 leave 안 된다거나 하는 정책
        return self.repo.leave_party(party_id=party_id, user_id=user_id)
