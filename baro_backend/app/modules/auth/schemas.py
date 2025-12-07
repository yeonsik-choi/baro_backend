from typing import Optional, List
from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class AuthUser(BaseModel):
    id: UUID
    kakao_id: str
    nickname: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    level: Optional[str] = None
    preferred_sports: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sportsmanship: Optional[float] = None



# 공통 Base: snake_case 필드명 + camelCase alias
class BaseSchema(BaseModel):
    # pydantic v2 스타일 설정
    model_config = ConfigDict(
        populate_by_name=True, 
        from_attributes=True, 
    )


# ====== 요청 DTO ======

class LoginRequestDto(BaseSchema):
    # 프론트 JSON: { "kakaoAccessToken": "..." }
    kakao_access_token: str = Field(..., alias="kakaoAccessToken")


class SignUpRequestDto(BaseSchema):
    # 프론트 JSON: nickname, birthDate, gender, height, weight, muscleMass, skillLevel, favoriteSports
    nickname: str
    birth_date: date = Field(..., alias="birthDate")  # "yyyy-MM-dd" 문자열 → date로 파싱됨
    gender: str
    height: float
    weight: float
    muscle_mass: Optional[float] = Field(None, alias="muscleMass")
    skill_level: str = Field(..., alias="skillLevel")
    favorite_sports: List[str] = Field(default_factory=list, alias="favoriteSports")


class ProfileUpdateRequestDto(BaseSchema):
    # 프론트 JSON
    nickname: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    muscle_mass: Optional[float] = Field(None, alias="muscleMass")
    skill_level: Optional[str] = Field(None, alias="skillLevel")
    favorite_sports: Optional[List[str]] = Field(None, alias="favoriteSports")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ====== 응답 DTO ======

class UserDto(BaseSchema):
    
    id: UUID  
    kakao_id: str = Field(..., alias="kakaoId")
    nickname: str

    # 아직 회원가입 안한 신규 유저일 수 있으니 전부 Optional / 기본값
    birth_date: Optional[date] = Field(None, alias="birthDate")
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    muscle_mass: Optional[float] = Field(None, alias="muscleMass")
    skill_level: Optional[str] = Field(None, alias="skillLevel")
    favorite_sports: List[str] = Field(default_factory=list, alias="favoriteSports")

    sportsmanship: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None



class LoginResponseDto(BaseSchema):
    
    is_new_user: bool = Field(..., alias="isNewUser")
    access_token: Optional[str] = Field(None, alias="accessToken")
    user: Optional[UserDto] = None
