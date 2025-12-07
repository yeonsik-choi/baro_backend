# app/modules/auth/deps.py
from fastapi import Header, HTTPException, status, Depends
from uuid import UUID

from .service import verify_jwt_token, _get_user_row_by_id, _row_to_auth_user
from .schemas import AuthUser


async def get_current_auth_user(
    authorization: str = Header(None),
) -> AuthUser:
    """
    Authorization: Bearer <JWT> 헤더에서 토큰을 꺼내고,
    verify_jwt_token → user_profile 조회 → AuthUser 로 변환.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    token = authorization.removeprefix("Bearer ").strip()

    # 1) JWT 검증해서 user_id 얻기
    try:
        user_id: UUID = verify_jwt_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # 2) Supabase user_profile 에서 row 가져오기
    try:
        user_row = _get_user_row_by_id(user_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 3) row → AuthUser 매핑
    auth_user = _row_to_auth_user(user_row)
    return auth_user


async def get_current_user_id(
    auth_user: AuthUser = Depends(get_current_auth_user),
) -> UUID:
    """
    Party 모듈처럼 user_id(UUID)만 필요할 때 쓰는 간단한 의존성.
    """
    return auth_user.id
