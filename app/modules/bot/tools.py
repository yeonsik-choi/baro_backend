# app/tools.py
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from .weather import get_simple_weather

from app.db import get_profiled_facilities, get_nearby_parties


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "저체중"
    if bmi < 23:
        return "정상"
    if bmi < 25:
        return "과체중"
    return "비만"

def _activity_multiplier(level: str) -> float:
    base = {"낮음": 28, "중간": 33, "높음": 38}
    return base.get(level, base["중간"])

@tool
def profile_based_sports_facilities(
    user_lat: float,
    user_lon: float,
    preferred_sports: Optional[List[str]] = None,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    preferred_intensity: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    사용자 프로필(위치, 선호 종목, 나이, 성별, 강도)을 기반으로 운동 시설을 추천합니다.
    """
    return get_profiled_facilities(
        user_lat=user_lat,
        user_lon=user_lon,
        preferred_sports=preferred_sports,
        age=age,
        gender=gender,
        preferred_intensity=preferred_intensity,
        limit=limit,
    )

@tool
def current_weather(user_lat: float, user_lon: float) -> str:
    """
    현재 사용자의 위치(위도/경도)를 기준으로 날씨 정보를 조회합니다.
    """
    info = get_simple_weather(user_lat, user_lon)
    if info is None:
        return "날씨 정보를 가져올 수 없습니다."
    
    temp = info["temp_c"]
    cond = info["condition"]
    if temp is None:
        return f"현재 날씨: {cond}"
    return f"현재 기온: {temp:.1f}°C, 날씨: {cond}"

@tool
def weight_management_plan(
    height_cm: float,
    weight_kg: float,
    goal_weight_kg: Optional[float] = None,
    weekly_goal_kg: float = 0.5,
    activity_level: str = "중간",
) -> Dict[str, Any]:
    """
    체중 관리 및 다이어트 상담을 위한 도구입니다.
    
    Args:
        height_cm: 키 (필수, context에서 가져옴)
        weight_kg: 현재 체중 (필수, context에서 가져옴)
        goal_weight_kg: 목표 체중 (선택 사항. 사용자가 대화 중에 말했으면 입력, 없으면 None)
        weekly_goal_kg: 주당 감량/증량 목표 (기본값 0.5kg)
        
    Returns:
        BMI 정보, 유지 칼로리, (목표가 있을 경우) 목표 달성 기간 및 권장 칼로리
    """

    height_m = height_cm / 100
    if height_m <= 0 or weight_kg <= 0:
        return {"error": "키와 체중은 0보다 커야 합니다."}

    bmi = weight_kg / (height_m**2)
    bmi_cat = _bmi_category(bmi)
    kcal_per_kg = _activity_multiplier(activity_level)
    maintenance_kcal = weight_kg * kcal_per_kg

    result = {
        "bmi": round(bmi, 2),
        "bmi_category": bmi_cat,
        "maintenance_kcal": int(maintenance_kcal),
        "current_weight": weight_kg,
        "height": height_cm,
    }

    # 목표 체중이 있는 경우에만 상세 계획 계산
    if goal_weight_kg is not None:
        diff = goal_weight_kg - weight_kg
        direction = "감량" if diff < 0 else "증량" if diff > 0 else "유지"
        safe_weekly = max(0.1, min(abs(weekly_goal_kg), 1.0))
        
        # 1kg ≈ 7700kcal
        daily_delta_kcal = safe_weekly * 7700 / 7
        estimated_weeks = abs(diff) / safe_weekly if safe_weekly > 0 else 0

        if direction == "감량":
            target_kcal = max(maintenance_kcal - daily_delta_kcal, maintenance_kcal * 0.7)
        elif direction == "증량":
            target_kcal = maintenance_kcal + daily_delta_kcal
        else:
            target_kcal = maintenance_kcal

        result.update({
            "has_goal": True,
            "goal_weight_kg": goal_weight_kg,
            "direction": direction,
            "estimated_weeks": round(estimated_weeks, 1),
            "target_kcal": int(target_kcal),
            "weekly_goal_kg": safe_weekly
        })
    else:
        result["has_goal"] = False

    return result

@tool
def nearby_parties(
    user_lat: float,
    user_lon: float,
    max_distance_km: float = 5.0,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    주변 운동 파티(모임)를 찾습니다.
    """
    return get_nearby_parties(
        user_lat=user_lat,
        user_lon=user_lon,
        max_distance_km=max_distance_km,
        limit=limit,
    )