# app/modules/party/repository.py

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from .schemas import CreatePartyRequest, Party, PartyMember
from app.modules.auth.service import _sb_get, _sb_post, _sb_patch

TABLE_PARTY = "party"
TABLE_PARTY_MEMBER = "party_member"


def _row_to_party_member(row: Dict) -> PartyMember:
    """
    party_member row -> PartyMember DTO 변환
    sportsmanship 은 user_profile 에 있으니까 일단 None으로 두고,
    나중에 필요하면 조인해서 채워 넣으면 됨.
    """
    return PartyMember(
        party_id=row["party_id"],
        user_id=row["user_id"],
        nickname=row.get("nickname") or "",
        role=row.get("role") or "member",
        status=row.get("status") or "joined",
        joined_at=row.get("joined_at") or "",
        sportsmanship=None,
    )


def _build_party(
    party_row: Dict,
    members: List[PartyMember],
    user_id: Optional[UUID],
) -> Party:
    """
    party + party_member 목록 -> Party DTO 한 개로 조합
    current, is_joined 계산
    """
    joined_members = [m for m in members if m.status == "joined"]
    current = len(joined_members)

    is_joined = False
    if user_id is not None:
        uid_str = str(user_id)
        is_joined = any(
            m.user_id == uid_str and m.status == "joined" for m in members
        )

    # capacity / capapcity 둘 다 대응
    capacity = party_row.get("capacity")
    if capacity is None:
        capacity = party_row.get("capapcity")
    if capacity is None:
        capacity = 0

    return Party(
        party_id=str(party_row["id"]),
        title=party_row["title"],
        sport=party_row["sport"],
        place=party_row.get("place") or "",
        description=party_row.get("description") or "",
        date=party_row.get("date") or "",
        start_time=party_row.get("start_time") or "",
        end_time=party_row.get("end_time") or "",
        capacity=capacity,
        current=current,
        host_id=party_row["host_id"],
        status=party_row.get("status") or "open",
        members=joined_members,
        is_joined=is_joined,
        created_at=party_row.get("created_at") or "",
        place_lat=party_row.get("place_lat"),
        place_lng=party_row.get("place_lng"),
    )


class PartyRepository:
    """
    Supabase REST(_sb_get/_sb_post/_sb_patch)로
    party, party_member 테이블을 직접 때리는 레이어
    """

    # 리스트
    def list_parties(self, user_id: Optional[UUID]) -> List[Party]:
        # 1) party 전체 조회
        party_rows = _sb_get(
            TABLE_PARTY,
            {
                "select": (
                    "id,title,sport,place,description,date,"
                    "start_time,end_time,capacity,capapcity,current,"
                    "host_id,status,created_at,place_lat,place_lng"
                ),
                "order": "created_at.desc",
            },
        )

        if not party_rows:
            return []

        # 2) party_id 리스트 만들기
        party_ids = [str(r["id"]) for r in party_rows]
        in_list = ",".join(party_ids)

        # 3) 해당 party 들의 멤버 전체 조회
        member_rows: List[Dict] = []
        if party_ids:
            member_rows = _sb_get(
                TABLE_PARTY_MEMBER,
                {
                    "select": "id,party_id,user_id,nickname,role,joined_at,status",
                    "party_id": f"in.({in_list})",
                },
            )

        # 4) party_id 기준으로 멤버 묶기
        members_by_party: Dict[str, List[PartyMember]] = {}
        for row in member_rows:
            pid = str(row["party_id"])
            members_by_party.setdefault(pid, []).append(_row_to_party_member(row))

        # 5) Party DTO 리스트로 변환
        result: List[Party] = []
        for p in party_rows:
            pid = str(p["id"])
            members = members_by_party.get(pid, [])
            result.append(_build_party(p, members, user_id))

        return result

    # 상세
    def get_party(self, party_id: str, user_id: Optional[UUID]) -> Party:
        party_rows = _sb_get(
            TABLE_PARTY,
            {
                "select": (
                    "id,title,sport,place,description,date,"
                    "start_time,end_time,capacity,capapcity,current,"
                    "host_id,status,created_at,place_lat,place_lng"
                ),
                "id": f"eq.{party_id}",
                "limit": 1,
            },
        )
        if not party_rows:
            raise KeyError("party not found")

        party_row = party_rows[0]

        member_rows = _sb_get(
            TABLE_PARTY_MEMBER,
            {
                "select": "id,party_id,user_id,nickname,role,joined_at,status",
                "party_id": f"eq.{party_id}",
            },
        )
        members = [_row_to_party_member(r) for r in member_rows]

        return _build_party(party_row, members, user_id)

    # 생성
    def create_party(self, user_id: UUID, req: CreatePartyRequest) -> Party:
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1) party insert
        party_body = {
            "title": req.title,
            "sport": req.sport,
            "place": req.place,
            "description": req.description,
            "date": req.date,
            "start_time": req.start_time,
            "end_time": req.end_time,
            "capacity": req.capacity,
            "current": 1,  # host 본인
            "host_id": str(user_id),
            "status": "open",
            "created_at": now_iso,
            "place_lat": req.place_lat,
            "place_lng": req.place_lng,
        }
        party_row = _sb_post(TABLE_PARTY, party_body)
        party_id = str(party_row["id"])

        # 2) host 멤버 insert
        member_body = {
            "party_id": party_id,
            "user_id": str(user_id),
            # TODO: user_profile에서 닉네임 가져오거나, 서비스에서 주입받아 넣기
            "nickname": "",
            "role": "host",
            "status": "joined",
            "joined_at": now_iso,
        }
        _sb_post(TABLE_PARTY_MEMBER, member_body)

        # 3) 완성된 Party 리턴 (멤버/현재 인원까지 포함)
        return self.get_party(party_id=party_id, user_id=user_id)

    # 참여
    def join_party(self, party_id: str, user_id: UUID) -> Party:
        uid_str = str(user_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1) 이미 멤버인지 확인
        existing = _sb_get(
            TABLE_PARTY_MEMBER,
            {
                "select": "id,party_id,user_id,nickname,role,joined_at,status",
                "party_id": f"eq.{party_id}",
                "user_id": f"eq.{uid_str}",
                "limit": 1,
            },
        )

        if not existing:
            # 없으면 새로 insert
            member_body = {
                "party_id": party_id,
                "user_id": uid_str,
                "nickname": "",
                "role": "member",
                "status": "joined",
                "joined_at": now_iso,
            }
            _sb_post(TABLE_PARTY_MEMBER, member_body)
        else:
            # 있으면 status 갱신(예: left -> joined)
            row = existing[0]
            if row.get("status") != "joined":
                _sb_patch(
                    TABLE_PARTY_MEMBER,
                    {"id": f"eq.{row['id']}"},
                    {"status": "joined", "joined_at": now_iso},
                )

        # 2) joined 인원 다시 세서 current 업데이트
        member_rows = _sb_get(
            TABLE_PARTY_MEMBER,
            {
                "select": "id,party_id,user_id,status",
                "party_id": f"eq.{party_id}",
            },
        )
        joined_count = sum(1 for r in member_rows if r.get("status") == "joined")
        _sb_patch(
            TABLE_PARTY,
            {"id": f"eq.{party_id}"},
            {"current": joined_count},
        )

        # 3) 최종 Party 반환
        return self.get_party(party_id=party_id, user_id=user_id)

    # 탈퇴
    def leave_party(self, party_id: str, user_id: UUID) -> Party:
        uid_str = str(user_id)

        # 1) 멤버 row 찾기
        existing = _sb_get(
            TABLE_PARTY_MEMBER,
            {
                "select": "id,party_id,user_id,nickname,role,joined_at,status",
                "party_id": f"eq.{party_id}",
                "user_id": f"eq.{uid_str}",
                "limit": 1,
            },
        )
        if not existing:
            # 애초에 참가한 적이 없으면 그냥 현재 상태 반환해도 되고, 에러를 던져도 됨
            return self.get_party(party_id=party_id, user_id=user_id)

        row = existing[0]
        if row.get("status") == "joined":
            # joined 상태인 경우에만 left로 변경
            _sb_patch(
                TABLE_PARTY_MEMBER,
                {"id": f"eq.{row['id']}"},
                {"status": "left"},
            )

        # 2) joined 인원 다시 세서 current 업데이트
        member_rows = _sb_get(
            TABLE_PARTY_MEMBER,
            {
                "select": "id,party_id,user_id,status",
                "party_id": f"eq.{party_id}",
            },
        )
        joined_count = sum(1 for r in member_rows if r.get("status") == "joined")
        _sb_patch(
            TABLE_PARTY,
            {"id": f"eq.{party_id}"},
            {"current": joined_count},
        )

        # 3) 최종 Party 반환
        return self.get_party(party_id=party_id, user_id=user_id)
