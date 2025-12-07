from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 모듈별 라우터 임포트
from app.modules.auth.router import auth_router, users_router 
from app.modules.bot.router import router as bot_router
from app.modules.party.router import router as party_router
from app.modules.message.router import router as message_router

app = FastAPI(
    title="Baro Backend API",
    version="0.1.0",
    description="Baro 운동 추천 앱을 위한 백엔드 API"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(bot_router)
app.include_router(party_router)
app.include_router(message_router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Baro Server is Running"}