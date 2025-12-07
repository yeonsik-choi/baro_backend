# app/modules/auth/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID

from app.modules.auth.schemas import (
    LoginRequestDto,
    LoginResponseDto,
    SignUpRequestDto,
    ProfileUpdateRequestDto,
    UserDto,
)
from app.modules.auth.service import (
    login_with_kakao,
    create_jwt_token,
    verify_jwt_token,
    sign_up,
    update_profile,
    get_user,
    delete_user,
)

# ----------------- 공통: 토큰 파싱 -----------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/kakao-login")

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    try:
        user_id = verify_jwt_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id


# ----------------- /auth 라우터 -----------------

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/kakao-login", response_model=LoginResponseDto)
def kakao_login_endpoint(req: LoginRequestDto):
    try:
        # login_with_kakao 가 이제 (auth_user, is_new_user) 튜플을 돌려줌
        auth_user, is_new = login_with_kakao(req.kakao_access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    jwt_token = create_jwt_token(auth_user.id)

    # AuthUser -> UserDto 수동 매핑
    user_dto = UserDto(
        id=auth_user.id,
        kakao_id=auth_user.kakao_id,
        nickname=auth_user.nickname or "",
        birth_date=None,  # 아직은 생년월일을 안 받으니까 None

        gender=auth_user.gender,
        height=auth_user.height_cm,
        weight=auth_user.weight_kg,
        muscle_mass=None,
        skill_level=auth_user.level,
        favorite_sports=auth_user.preferred_sports or [],
        sportsmanship=auth_user.sportsmanship or 0.0,
        latitude=auth_user.latitude,
        longitude=auth_user.longitude,
    )

    return LoginResponseDto(
        is_new_user=is_new,
        access_token=jwt_token,
        user=user_dto,
    )


@auth_router.post("/sign-up", response_model=UserDto)
def sign_up_endpoint(
    req: SignUpRequestDto,
    user_id: UUID = Depends(get_current_user_id),
):
    auth_user = sign_up(user_id, req)
    
    return UserDto(
        id=auth_user.id,
        kakao_id=auth_user.kakao_id,
        nickname=auth_user.nickname or "",
        birth_date=None,
        gender=auth_user.gender,
        height=auth_user.height_cm,
        weight=auth_user.weight_kg,
        muscle_mass=None,
        skill_level=auth_user.level,
        favorite_sports=auth_user.preferred_sports or [],
        sportsmanship=auth_user.sportsmanship or 0.0,
        latitude=auth_user.latitude,
        longitude=auth_user.longitude,
    )


@auth_router.post("/logout")
def logout(user_id: UUID = Depends(get_current_user_id)):
    
    return {"detail": "logged out"}


# ----------------- /users 라우터 -----------------

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/me", response_model=UserDto)
def get_my_profile(user_id: UUID = Depends(get_current_user_id)):
    try:
        auth_user = get_user(user_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")

    return UserDto(
        id=auth_user.id,
        kakao_id=auth_user.kakao_id,
        nickname=auth_user.nickname or "",
        birth_date=None,
        gender=auth_user.gender,
        height=auth_user.height_cm,
        weight=auth_user.weight_kg,
        muscle_mass=None,
        skill_level=auth_user.level,
        favorite_sports=auth_user.preferred_sports or [],
        sportsmanship=auth_user.sportsmanship or 0.0,
        latitude=auth_user.latitude,
        longitude=auth_user.longitude,
    )


@users_router.patch("/me/profile", response_model=UserDto)
def update_my_profile(
    req: ProfileUpdateRequestDto,
    user_id: UUID = Depends(get_current_user_id),
):
    auth_user = update_profile(user_id, req)
    return UserDto(
        id=auth_user.id,
        kakao_id=auth_user.kakao_id,
        nickname=auth_user.nickname or "",
        birth_date=None,
        gender=auth_user.gender,
        height=auth_user.height_cm,
        weight=auth_user.weight_kg,
        muscle_mass=None,
        skill_level=auth_user.level,
        favorite_sports=auth_user.preferred_sports or [],
        sportsmanship=auth_user.sportsmanship or 0.0,
        latitude=auth_user.latitude,
        longitude=auth_user.longitude,
    )


@users_router.delete("/me")
def delete_account(user_id: UUID = Depends(get_current_user_id)):
    delete_user(user_id)
    return {"detail": "account deleted"}
