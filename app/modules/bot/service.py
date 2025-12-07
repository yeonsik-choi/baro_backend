from datetime import datetime
import logging

from .graph import run_agent
from .weather import get_simple_weather
from app.modules.bot.schemas import ChatRequest
from openai import RateLimitError
from app.core.supabase import supabase_client  # Supabase 클라이언트 임포트

logger = logging.getLogger(__name__)

def calculate_age(birth_date_str: str) -> int:
    """YYYY-MM-DD 문자열을 받아 만 나이를 계산"""
    if not birth_date_str:
        return 0
    try:
        birth = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except:
        return 0

def is_weather_only_query(msg: str) -> bool:
    text = msg.replace(" ", "")
    weather_kw = ["날씨", "비와", "눈와", "기온어때", "기온이어때"]
    sports_kw = ["운동", "헬스장", "수영장", "운동장", "시설", "추천", "코트", "체육관"]
    return any(k in text for k in weather_kw) and not any(k in text for k in sports_kw)

def process_bot_message(req: ChatRequest) -> str:
    # 1. 날씨만 묻는 경우 (기존 로직 유지)
    if is_weather_only_query(req.message) and req.latitude and req.longitude:
        info = get_simple_weather(req.latitude, req.longitude)
        if info is None:
            return "지금은 기상청 날씨 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."
        
        temp = info["temp_c"]
        cond = info["condition"]
        
        if temp is None:
            return f"현재 하늘 상태는 {cond}입니다."
        else:
            return f"현재 기온은 약 {temp:.1f}도이고, 하늘 상태는 {cond}입니다."

    # 2. 챗봇 에이전트에게 전달할 사용자 컨텍스트 생성 (기존 로직 유지)
    user_context = []
    if req.nickname: user_context.append(f"이름: {req.nickname}")
    if req.gender: user_context.append(f"성별: {req.gender}")
    if req.birth_date:
        age = calculate_age(req.birth_date)
        if age > 0: user_context.append(f"나이: {age}세")
    elif req.age:
        user_context.append(f"나이: {req.age}세")
    if req.height: user_context.append(f"키: {req.height}cm")
    if req.weight: user_context.append(f"체중: {req.weight}kg")
    if req.muscle_mass: user_context.append(f"골격근량: {req.muscle_mass}kg")
    if req.skill_level: user_context.append(f"운동 숙련도: {req.skill_level}")
    if req.favorite_sports: 
        sports_str = ", ".join(req.favorite_sports)
        user_context.append(f"선호 종목: {sports_str}")
    if req.latitude and req.longitude:
        user_context.append(f"현재 위치(위도: {req.latitude}, 경도: {req.longitude})")

    system_instruction = ""
    if user_context:
        system_instruction = "[사용자 프로필 정보]\n" + "\n".join(user_context) + "\n\n이 정보를 바탕으로 사용자의 질문에 답변해.\n"
    
    final_prompt = system_instruction + req.message

    try:
        thread_id = getattr(req, "thread_id", getattr(req, "user_id", "default_global_thread"))
        thread_id = str(thread_id)
        
        # 1. 세션용 (TIMESTAMP 타입이라고 가정 시 문자열 사용)
        session_created_at = int(datetime.now().timestamp() * 1000)
        
        # 2. 메시지용 (BIGINT 타입이므로 정수 사용 - 밀리초 단위)
        message_timestamp = int(datetime.now().timestamp() * 1000)

        # ---------------------------------------------------------------------------
        # [DB 저장] 1. 세션 정보 저장 (chat_session 테이블)
        # 스키마: id, title, last_message, created_at
        # ---------------------------------------------------------------------------
        try:
            session_data = {
                "id": thread_id,
                "title": f"대화 {thread_id[:8]}",
                "last_message": req.message,
                "created_at": session_created_at  # [수정 2] 정수형 변수로 교체
            }
            supabase_client.schema("app").table("chat_session").upsert(session_data).execute()
        except Exception as e:
            logger.error(f"Failed to save session to Supabase: {e}")

        # ---------------------------------------------------------------------------
        # [DB 저장] 2. 사용자 메시지 저장 (chat_messages 테이블)
        # 스키마: id, session_id, text, sender, timestamp
        # ---------------------------------------------------------------------------
        try:
            supabase_client.schema("app").table("chat_messages").insert({
                "session_id": thread_id,
                "sender": "user",
                "text": req.message,
                "timestamp": message_timestamp  # <--- 정수(bigint)로 입력
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")

        # [Agent 실행]
        bot_response = run_agent(final_prompt, thread_id)

        # ---------------------------------------------------------------------------
        # [DB 저장] 3. 챗봇 응답 저장 (chat_messages 테이블)
        # ---------------------------------------------------------------------------
        try:
            # 챗봇 응답 시간도 정수로 생성
            bot_timestamp = int(datetime.now().timestamp() * 1000)
            
            supabase_client.schema("app").table("chat_messages").insert({
                "session_id": thread_id,
                "sender": "assistant",
                "text": bot_response,
                "timestamp": bot_timestamp # <--- 정수(bigint)로 입력
            }).execute()

            # 3-2. 세션 last_message 업데이트
            supabase_client.schema("app").table("chat_session").update({
                "last_message": bot_response
            }).eq("id", thread_id).execute()

        except Exception as e:
            logger.error(f"Failed to save bot message: {e}")

        return bot_response
        
    except RateLimitError:
        logger.warning("OpenAI rate limit exceeded while processing bot message")
        return "지금은 챗봇 서버에 요청이 너무 많아서 잠시 응답을 줄 수 없어요. 잠시 후 다시 시도해 주세요."
    except Exception:
        logger.exception("Unexpected error while calling agent")
        return "챗봇 응답 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."