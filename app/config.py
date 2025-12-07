# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KMA_API_KEY = os.getenv("KMA_API_KEY")
SUPABASE_AUTH_SCHEMA = "app"
SUPABASE_USERS_TABLE = "user_profile"
SUPABASE_PROFILES_TABLE = "user_profile"


if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Supabase 환경변수(SUPABASE_URL, SUPABASE_ANON_KEY)를 설정하세요.")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY를 설정하세요.")

if not KMA_API_KEY:
    print("경고: KMA_API_KEY가 설정되어 있지 않습니다. 날씨 기반 필터는 비활성 상태입니다.")