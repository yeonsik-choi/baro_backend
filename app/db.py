# app/db.py
import math
import requests
from typing import List, Optional, Dict, Any

from .config import SUPABASE_URL, SUPABASE_ANON_KEY
from app.modules.bot.weather import is_indoor_only

TABLE_NAME = "songpa_sports_data"

# ------------------ 공통 요청 헤더 ------------------ #
def _base_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Accept-Profile": "sports_data",  # 스키마
    }

# ------------------ 기존 시설 조회 ------------------ #
def _fetch_all_facilities() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    params = {
        "select": "faci_cd,faci_nm,faci_addr,faci_lat,faci_lot,ftype_nm,inout_gbn_nm"
    }
    resp = requests.get(url, params=params, headers=_base_headers(), timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase 요청 실패: {resp.status_code} - {resp.text}")
    return resp.json()


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ------------------ 문자열 / 나이 band helper ------------------ #
def _norm(text: str) -> str:
    return (text or "").replace(" ", "").lower()


def _age_to_band(age: int) -> str:
    if age < 20:
        return "10대"
    elif age < 30:
        return "20대"
    elif age < 40:
        return "30대"
    elif age < 50:
        return "40대"
    elif age < 60:
        return "50대"
    elif age < 70:
        return "60대"
    else:
        return "70대 이상"


def _match_sport(main_text: str, sport_name: str) -> bool:
    """ftype_nm 안에 특정 종목명이 포함되는지 (공백 제거 후 부분문자열 매칭)."""
    return _norm(sport_name) in _norm(main_text)


# ------------------ exercise_methods (강도) 조회 ------------------ #
def _fetch_exercise_methods() -> Dict[str, str]:
    """
    sports_nm -> intensity 매핑 dict 반환.
    """
    url = f"{SUPABASE_URL}/rest/v1/exercise_methods"
    params = {"select": "sports_nm,intensity"}
    resp = requests.get(url, params=params, headers=_base_headers(), timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase exercise_methods 실패: {resp.status_code} - {resp.text}")
    rows = resp.json()

    mapping: Dict[str, str] = {}
    for row in rows:
        name = row.get("sports_nm")
        intensity = row.get("intensity")
        if name and intensity:
            mapping[_norm(name)] = intensity  # 예: '축구' -> '고'
    return mapping

# ------------------ sports_pref (연령/성별별 선호 종목) 조회 ------------------ #
def _fetch_age_gender_pref_sports(age_band: str, gender: str) -> List[str]:
    """
    sports_pref 테이블에서 해당 나이대 + 성별의 sports_nm 리스트 반환.
    sports_nm은 '축구, 테니스, 야구' 형태라 split해서 리스트로 만듦.
    """
    url = f"{SUPABASE_URL}/rest/v1/sports_pref"
    params = {
        "select": "sports_nm",
        "ages": f"eq.{age_band}",
        "gender": f"eq.{gender}",
    }
    resp = requests.get(url, params=params, headers=_base_headers(), timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase sports_pref 실패: {resp.status_code} - {resp.text}")
    rows = resp.json()
    if not rows:
        return []

    sports_set = set()
    for row in rows:
        s = row.get("sports_nm") or ""
        for sp in s.split(","):
            sp = sp.strip()
            if sp:
                sports_set.add(sp)
    return list(sports_set)

def get_profiled_facilities(
    user_lat: float,
    user_lon: float,
    preferred_sports: Optional[List[str]] = None,  # 사용자가 좋아한다고 적어둔 종목들
    age: Optional[int] = None,
    gender: Optional[str] = None,                  # '남' 또는 '여'
    preferred_intensity: Optional[str] = None,     # '저', '중', '고' 중 하나
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    거리 + 선호 스포츠 + 나이/성별 + 운동강도 + 연령별 선호스포츠를 반영한 추천.
    """

    facilities = _fetch_all_facilities()
    intensity_map = _fetch_exercise_methods()
    # 날씨 보고 실내만 추천해야 하는지 결정
    indoor_only = is_indoor_only(user_lat, user_lon)
    print(f"[recommend-debug] indoor_only={indoor_only}", flush=True)

    age_band: Optional[str] = None
    age_gender_pref_sports: List[str] = []
    if age is not None:
        age_band = _age_to_band(age)
    if age_band and gender:
        age_gender_pref_sports = _fetch_age_gender_pref_sports(age_band, gender)

    # 가중치 (1~6순위)
    W_DIST = 0.2
    W_PREF = 0.2
    W_AGE = 0.2
    W_GENDER = 0.2
    W_INTENSITY = 0.05
    W_AGE_SPORTS = 0.05

    preferred_sports_norm = [
        _norm(s) for s in (preferred_sports or [])
    ]
    age_gender_pref_norm = [_norm(s) for s in age_gender_pref_sports]

    results: List[Dict[str, Any]] = []

    for row in facilities:
        if indoor_only and row.get("inout_gbn_nm") != "실내":
            continue
        try:
            faci_lat = float(row["faci_lat"])
            faci_lon = float(row["faci_lot"])
        except (TypeError, ValueError):
            continue

        ftype_nm = row.get("ftype_nm") or ""
        distance_km = _haversine(user_lat, user_lon, faci_lat, faci_lon)

        # 1) 거리 점수 (0~1)
        D_MAX = 5.0  # 5km까지 유효
        dist_score = max(0.0, (D_MAX - distance_km) / D_MAX)

        # 2) 선호 스포츠 점수
        pref_score = 0.0
        if preferred_sports_norm:
            for sp in preferred_sports_norm:
                if sp in _norm(ftype_nm):
                    pref_score = 1.0
                    break

        # 3) 나이/성별 기반 (sports_pref)
        age_score = 0.0
        gender_score = 0.0
        age_sports_score = 0.0

        if age_gender_pref_norm:
            for sp in age_gender_pref_norm:
                if sp in _norm(ftype_nm):
                    # 같은 sports_pref 세트를 기반으로 하지만
                    # 가중치를 다르게 줘서 우선순위 차이를 둔다
                    age_score = 1.0
                    gender_score = 1.0
                    age_sports_score = 1.0
                    break

        # 5) 운동 강도 일치 여부 (exercise_methods)
        intensity_score = 0.0
        if preferred_intensity:
            facility_intensity = None
            for sports_key, inten in intensity_map.items():
                if sports_key in _norm(ftype_nm):
                    facility_intensity = inten
                    break
            if facility_intensity and facility_intensity == preferred_intensity:
                intensity_score = 1.0

        total_score = (
            W_DIST * dist_score
            + W_PREF * pref_score
            + W_AGE * age_score
            + W_GENDER * gender_score
            + W_INTENSITY * intensity_score
            + W_AGE_SPORTS * age_sports_score
        )

        results.append(
            {
                "faci_cd": row["faci_cd"],
                "faci_nm": row["faci_nm"],
                "faci_addr": row["faci_addr"],
                "ftype_nm": row["ftype_nm"],
                "inout_gbn_nm": row["inout_gbn_nm"],
                "faci_lat": faci_lat,
                "faci_lot": faci_lon,
                "distance_km": round(distance_km, 2),
                "score": round(total_score, 3),
                "detail_scores": {
                    "distance": round(dist_score, 3),
                    "preferred_sport": pref_score,
                    "age": age_score,
                    "gender": gender_score,
                    "intensity": intensity_score,
                    "age_sports": age_sports_score,
                },
            }
        )

    # 점수 높은 순으로 정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "indoor_only": indoor_only,
        "facilities": results[:limit],
    }

# sample 스키마(파티 테이블용) 헤더
def _sample_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Accept-Profile": "sample",      # Supabase 좌측 상단 schema 이름
    }

# ------------------ 파티 정보 조회 ------------------ #
def get_nearby_parties(
    user_lat: float,
    user_lon: float,
    max_distance_km: float = 5.0,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Supabase sample.parties 테이블에서
    사용자 근처에서 모집 중인 파티를 거리순으로 반환.
    """

    url = f"{SUPABASE_URL}/rest/v1/parties"
    params = {
        # 필요 컬럼만 골라서 가져오기
        "select": "id,title,sports_nm,place,lat,lon,date,start_time,end_time,max_members,notes,status",
        "status": "eq.recruiting",  # 모집 중인 파티만
    }

    resp = requests.get(url, params=params, headers=_sample_headers(), timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Supabase parties 요청 실패: {resp.status_code} - {resp.text}")

    rows = resp.json()

    results: List[Dict[str, Any]] = []
    for row in rows:
        try:
            party_lat = float(row["lat"])
            party_lon = float(row["lon"])
        except (TypeError, ValueError):
            continue

        distance_km = _haversine(user_lat, user_lon, party_lat, party_lon)

        # 너무 먼 파티는 제외 (예: 5km 이상)
        if distance_km > max_distance_km:
            continue

        results.append(
            {
                "id": row["id"],
                "title": row.get("title"),
                "sports_nm": row.get("sports_nm"),
                "place": row.get("place"),
                "lat": party_lat,
                "lon": party_lon,
                "date": row.get("date"),
                "start_time": row.get("start_time"),
                "end_time": row.get("end_time"),
                "max_members": row.get("max_members"),
                "notes": row.get("notes"),
                "status": row.get("status"),
                "distance_km": round(distance_km, 2),
            }
        )

    # 거리 가까운 순서로 정렬
    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]