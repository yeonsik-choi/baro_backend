# app/modules/auth/service.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from typing import Dict, Optional, Any, List, Tuple
from uuid import UUID

import requests
from jose import jwt, JWTError

from .schemas import AuthUser, SignUpRequestDto, ProfileUpdateRequestDto
from app.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_AUTH_SCHEMA,
    SUPABASE_USERS_TABLE,   
)
from app.config_auth import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRE_DAYS,
    KAKAO_USERINFO_URL,
)

# ============================================================
# 공통 Supabase 헬퍼
# ============================================================

def _sb_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Accept-Profile": SUPABASE_AUTH_SCHEMA,
        "Content-Type": "application/json",
    }


def _sb_get(table: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.get(url, params=params, headers=_sb_headers(), timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase GET 실패: {resp.status_code} - {resp.text}")
    return resp.json()


def _sb_post(table: str, body: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _sb_headers()
    headers["Prefer"] = "return=representation"
    resp = requests.post(url, json=body, headers=headers, timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase POST 실패: {resp.status_code} - {resp.text}")
    data = resp.json()
    return data[0] if data else {}


def _sb_patch(table: str, match: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = match.copy()
    headers = _sb_headers()
    headers["Prefer"] = "return=representation"
    resp = requests.patch(url, params=params, json=body, headers=headers, timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase PATCH 실패: {resp.status_code} - {resp.text}")
    data = resp.json()
    return data[0] if data else {}


def _sb_delete(table: str, match: Dict[str, str]) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = match.copy()
    resp = requests.delete(url, params=params, headers=_sb_headers(), timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase DELETE 실패: {resp.status_code} - {resp.text}")


# ============================================================
# Kakao API
# ============================================================

def get_kakao_profile(access_token: str) -> dict:
    """
    카카오 access token으로 /v2/user/me 호출해서 프로필 가져오기.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(KAKAO_USERINFO_URL, headers=headers, timeout=5)
    if not resp.ok:
        raise ValueError(f"Kakao API error: {resp.status_code} - {resp.text}")
    return resp.json()


# ============================================================
# JWT
# ============================================================

def create_jwt_token(user_id: UUID) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": exp,
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> UUID:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise JWTError("No sub")
        return UUID(sub)
    except JWTError as e:
        raise ValueError("Invalid token") from e


# ============================================================
# Supabase user_profile 접근 함수
# ============================================================

def _get_user_row_by_kakao(kakao_id: str) -> Optional[Dict[str, Any]]:
    """
    kakao_id 로 user_profile 에서 한 명 조회
    """
    rows = _sb_get(
        SUPABASE_USERS_TABLE,
        {
            "select": "uuid,kakao_id,nickname,birth_date,gender,height,weight,"
                      "muscle_mass,skill_level,favorite_sports,sportsmanship,"
                      "latitude,longitude",
            "kakao_id": f"eq.{kakao_id}",
            "limit": 1,
        },
    )
    return rows[0] if rows else None


def _get_user_row_by_id(user_id: UUID) -> Dict[str, Any]:
    """
    uuid 로 user_profile 에서 한 명 조회
    """
    rows = _sb_get(
        SUPABASE_USERS_TABLE,
        {
            "select": "uuid,kakao_id,nickname,birth_date,gender,height,weight,"
                      "muscle_mass,skill_level,favorite_sports,sportsmanship,"
                      "latitude,longitude",
            "uuid": f"eq.{user_id}",
            "limit": 1,
        },
    )
    if not rows:
        raise KeyError("user not found")
    return rows[0]


def _insert_user_row(kakao_id: str) -> Dict[str, Any]:
    """
    카카오 로그인 최초 시, user_profile 에 기본 row 하나 생성
    """
    return _sb_post(
        SUPABASE_USERS_TABLE,
        {
            "kakao_id": kakao_id,
            # 필요하면 기본값 더 넣어도 됨
            "sportsmanship": 0.0,
            "favorite_sports": [],
        },
    )


def _row_to_auth_user(
    user_row: Dict[str, Any],
    profile_row: Optional[Dict[str, Any]] = None,
    kakao_nickname: Optional[str] = None,
) -> AuthUser:
    """
    user_profile row → AuthUser 로 매핑
    profile_row 는 지금 구조에선 쓰지 않지만, 시그니처 유지
    """

    pref = user_row.get("favorite_sports") or user_row.get("favorite_sports")
    if isinstance(pref, str):
        preferred_sports = [s.strip() for s in pref.split(",") if s.strip()]
    else:
        preferred_sports = pref

    birth_date: Optional[date] = user_row.get("birth_date")
    age: Optional[int] = None
    # 필요하면 여기서 birth_date 기반으로 나이 계산 가능

    return AuthUser(
        id=UUID(user_row["uuid"]),
        kakao_id=user_row["kakao_id"],
        nickname=user_row.get("nickname") or kakao_nickname,
        age=age,
        gender=user_row.get("gender"),
        height_cm=user_row.get("height"),
        weight_kg=user_row.get("weight"),
        level=user_row.get("skill_level"),
        preferred_sports=preferred_sports,
        latitude=user_row.get("latitude"),
        longitude=user_row.get("longitude"),
        sportsmanship=user_row.get("sportsmanship"),
    )


# ============================================================
# 외부에서 쓰는 서비스 함수들
# ============================================================

def login_with_kakao(access_token: str) -> tuple[AuthUser, bool]:
    """
    1) 카카오에서 프로필 조회
    2) kakao_id 기준으로 Supabase users 에서 유저 생성/조회
    3) AuthUser + is_new_user 리턴
    """
    data = get_kakao_profile(access_token)

    kakao_id = str(data["id"])
    profile = data.get("kakao_account", {}).get("profile", {})

    nickname = profile.get("nickname")

    # 1) users 테이블에서 kakao_id 로 검색
    user_row = _get_user_row_by_kakao(kakao_id)
    if not user_row:
        # 신규 가입 → users 에 row 만들기
        user_row = _insert_user_row(kakao_id)
        is_new = True
    else:
        is_new = False

    user_id = UUID(user_row["uuid"])

    
    auth_user = _row_to_auth_user(user_row, profile_row=None, kakao_nickname=nickname)

    return auth_user, is_new




def sign_up(user_id: UUID, req: SignUpRequestDto) -> AuthUser:
    """
    최초 회원가입(추가 정보 입력) → user_profile 에 바로 PATCH.
    """
    body: Dict[str, Any] = req.dict(exclude_none=True)

    if "favorite_sports" in body:
        body["favorite_sports"] = body.pop("favorite_sports")

    row = _sb_patch(
        SUPABASE_USERS_TABLE,
        {"uuid": f"eq.{user_id}"},
        body,
    )
    return _row_to_auth_user(row, None)


def update_profile(user_id: UUID, req: ProfileUpdateRequestDto) -> AuthUser:
    """
    프로필 수정 → user_profile 에 바로 PATCH.
    """
    body: Dict[str, Any] = req.dict(exclude_unset=True, exclude_none=True)

    if not body:
        # 수정할 내용이 없으면 현재 정보만 조회해서 반환
        user_row = _get_user_row_by_id(user_id)
        return _row_to_auth_user(user_row, None)

    if "favorite_sports" in body:
        body["favorite_sports"] = body.pop("favorite_sports")

    row = _sb_patch(
        SUPABASE_USERS_TABLE,
        {"uuid": f"eq.{user_id}"},
        body,
    )
    return _row_to_auth_user(row, None)


def get_user(user_id: UUID) -> AuthUser:
    """
    내 정보 조회 → user_profile 에서 uuid 로 SELECT.
    """
    user_row = _get_user_row_by_id(user_id)
    return _row_to_auth_user(user_row, None)


def delete_user(user_id: UUID) -> None:
    """
    계정 삭제 → user_profile 에서 uuid 로 DELETE.
    """
    _sb_delete(
        SUPABASE_USERS_TABLE,
        {"uuid": f"eq.{user_id}"},
    )
