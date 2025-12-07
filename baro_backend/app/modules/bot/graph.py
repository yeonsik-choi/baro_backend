# app/modules/bot/graph.py
import logging
import os
from contextlib import contextmanager

# LangChain / LangGraph 관련 임포트
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage

#  DB(Postgres) 기반 영속성 저장을 위한 라이브러리
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# 재시도 로직을 위한 라이브러리
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APITimeoutError

from app.config import OPENAI_API_KEY
from .tools import (
    profile_based_sports_facilities,
    current_weather,
    weight_management_plan,
    nearby_parties
)

logger = logging.getLogger(__name__)


DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")

# 모델 설정
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY,
    max_retries=0, 
)

tools = [
    profile_based_sports_facilities,
    current_weather,
    weight_management_plan,
    nearby_parties
]

SYSTEM_PROMPT = """
너는 '거리 기반 운동 추천 챗봇'이고 챗봇의 이름은 '바로'이다.

1) 주변 운동 시설 추천 (거리 기반)
- 사용자가 '근처', '주변', '운동할 곳', '운동 시설', '헬스장', '수영장', '운동장' 등
  주변에서 운동할 장소를 추천해 달라고 **명시적으로 요청하는 경우에만**
  profile_based_sports_facilities 도구를 정확히 한 번 호출한다.
- 이때 스코어가 가장 높은 3개의 시설을 골라,
  각 시설 이름(faci_nm), 운동 종류(ftype_nm), 실내/실외(inout_gbn_nm), 거리(km)를
  자연스러운 한국어 문단으로 요약해서 알려준다.
- 도구 결과에 indoor_only=true 가 명시된 경우에만
  앞에 '현재 날씨/기온을 고려해 실내 운동만 추천합니다.'라고 말한다.
  그렇지 않으면 그런 표현을 쓰지 않는다.

2) 날씨 질의
- 사용자가 '날씨 어때?', '지금 비와?', '눈와?', '기온 어때?'처럼
  **날씨만 물어보는 경우**에는,
  어떤 운동 관련 도구도 호출하지 말고 current_weather 도구만 한 번 호출한다.
- current_weather 결과를 사용하여
  '현재 기온은 몇 도이고, 하늘 상태는 맑음/비/눈입니다.'
  형태로 한두 문장만 짧게 답한다.
- 이때 운동 시설이나 운동 추천, 체중 관리는 절대 말하지 않는다.

3) 체중 관리 / 다이어트 상담
- 사용자가 질문 문장 안에서 **'체중', '몸무게', '살', '다이어트',
  '감량', '증량', '칼로리', '식단', '체지방', 'BMI'** 와 같은 단어를
  하나 이상 사용할 때에만 weight_management_plan 도구를 정확히 한 번 호출한다.
- 도구 결과의 BMI, 유지 칼로리, 목표 체중별 권장 섭취 열량과 예상 기간을
  한국어로 친절하게 풀어서 설명하되,
  항상 의학적 진단이 아니며, 필요 시 전문가(의사·영양사) 상담을 권유한다.
- 이 시나리오에서는 운동 시설 추천, 파티 추천, 날씨 정보는 섞지 않는다.

4) 운동 파티 / 같이 운동할 사람 찾기
- 사용자가 질문 문장 안에서 **'같이 운동', '운동할 사람', '같이 할 사람',
  '파티', '운동 파티', '번개', '운동 모임', '같이 뛰자', '같이 치자'** 등의
  단어를 사용하는 경우에는,
  nearby_parties 도구만 정확히 한 번 호출한다.
- 도구 결과가 있으면 사용자와의 거리 순으로 최대 3개의 파티를 골라,
  각 파티의 제목(title), 종목(sports_nm), 장소(place), 날짜(date),
  시간(start_time~end_time), 모집 인원(max_mem), 거리(km), 상태(모집 중/마감)을
  자연스러운 한국어로 요약해서 알려준다.
- 결과가 없으면 '현재 내 주변에서 모집 중인 운동 파티는 없습니다.'라고 부드럽게 알려준다.
- 이 시나리오에서는 체중 관리나 일반 운동 시설 추천, 날씨 정보는 섞지 않는다.

5) 중요한 우선순위 규칙
- 질문 문장 안에 **파티/모임 관련 단어(4번의 키워드)** 가 하나라도 있으면
  절대 weight_management_plan 을 호출하지 말고,
  nearby_parties 만 사용한다.
- 질문 문장 안에 **체중/다이어트 관련 단어(3번의 키워드)** 가 하나도 없으면
  weight_management_plan 도구를 호출하지 않는다.
- 질문이 1~4번 중 어디에도 명확히 속하지 않을 때에만
  도구를 사용하지 않고 일반 GPT처럼 답변한다.

6) 일반 운동 상담 / 잡담
- 사용자가 단순 운동 루틴, 스트레칭, 부상 예방, 동기부여, 잡담 등을 요청하면
  어떤 도구도 호출하지 말고, 일반 GPT처럼 자연스럽고 친근하게 대화한다.

요약:
- 시설 추천 → profile_based_sports_facilities **한 번**
- 날씨 질문 → current_weather **한 번**
- 체중/다이어트 → weight_management_plan **한 번**
- 파티/같이 운동 → nearby_parties **한 번**
- 서로 섞지 않는다.
"""


# Connection Pool 생성 (서버 생명주기 동안 유지)
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": None,
}

# DB 연결 풀 초기화
pool = ConnectionPool(
    conninfo=DB_CONNECTION_STRING,
    max_size=20,
    kwargs=connection_kwargs
)

# Postgres Checkpointer 생성
checkpointer = PostgresSaver(pool)


checkpointer.setup()

# Agent 생성 (DB Checkpointer 연결)
agent = create_react_agent(
    llm, 
    tools, 
    checkpointer=checkpointer,
    prompt=SYSTEM_PROMPT 
)

# [재시도 로직] Rate Limit 등의 에러 발생 시 자동 재시도
@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3), # 재시도 횟수 3회로 증가
    reraise=True
)
def invoke_agent_with_retry(user_message: str, config: dict):
   
    return agent.invoke(
        {
            "messages": [
                HumanMessage(content=user_message), 
            ]
        },
        config=config
    )

def run_agent(user_message: str, thread_id: str) -> str:
    try:
        # thread_id를 config에 설정
        config = {"configurable": {"thread_id": thread_id}}
        
        # 재시도 함수 호출
        result = invoke_agent_with_retry(user_message, config)
        
    except RateLimitError:
        logger.error("OpenAI Rate Limit Exceeded even after retries.")
        raise 
    except Exception as e:
        logger.exception("LangGraph agent.invoke 중 오류")
        raise

    ai_msg = result["messages"][-1]
    return ai_msg.content