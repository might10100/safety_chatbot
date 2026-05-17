"""
weather.py — 기상청 단기예보 날씨 자동 추출
공공데이터포털(data.go.kr) '기상청_단기예보 조회서비스' API 키 필요
"""
import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Streamlit Cloud Secrets 우선, 없으면 .env에서
try:
    import streamlit as st
    WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", os.getenv("WEATHER_API_KEY", ""))
except Exception:
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# 기상청 격자 좌표 (주요 도시)
GRID_MAP = {
    "서울": (60, 127), "강남": (61, 126), "강서": (58, 126),
    "부산": (98, 76),  "인천": (55, 124), "대구": (89, 90),
    "광주": (58, 74),  "대전": (67, 100), "울산": (102, 84),
    "수원": (60, 121), "창원": (90, 77),  "고양": (57, 128),
    "성남": (62, 123), "청주": (69, 106), "전주": (63, 89),
    "천안": (63, 110), "안양": (59, 123), "포항": (102, 94),
    "제주": (52, 38),  "춘천": (73, 134), "원주": (76, 122),
    "강릉": (92, 131), "여수": (73, 66),  "순천": (74, 68),
    "목포": (50, 67),  "구미": (84, 96),  "경주": (100, 91),
}


def get_grid(address: str) -> tuple:
    """주소에서 기상청 격자 좌표 추출"""
    for city, grid in GRID_MAP.items():
        if city in address:
            return grid
    return (60, 127)  # 기본값: 서울


def _get_base_time() -> tuple[str, str]:
    """가장 가까운 예보 발표 시각 반환 (3시간 단위: 0200/0500/0800/1100/1400/1700/2000/2300)"""
    now = datetime.now(KST)
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    base_h = max([h for h in base_hours if h <= now.hour], default=23)

    if now.hour < 2:
        base_dt = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0)
    else:
        base_dt = now.replace(hour=base_h, minute=0, second=0)

    return base_dt.strftime("%Y%m%d"), f"{base_h:02d}00"


# 하늘 상태 코드
SKY_MAP = {1: "맑음", 2: "구름조금", 3: "구름많음", 4: "흐림"}
SKY_ICON = {1: "☀️", 2: "🌤", 3: "⛅", 4: "☁️"}

# 강수 형태 코드
PTY_MAP = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기"}
PTY_ICON = {0: "", 1: "🌧", 2: "🌨", 3: "❄️", 4: "⛈"}

# 풍속 위험도 (건설 현장 기준)
def wind_level(wsd: float) -> tuple[str, str]:
    """풍속(m/s) → (등급, 색상힌트)"""
    if wsd < 4:   return "약풍", "safe"
    if wsd < 9:   return "보통", "caution"
    if wsd < 14:  return "강풍주의", "warning"
    return "강풍위험", "danger"


def fetch_weather(address: str, date: str = None) -> dict:
    """
    기상청 단기예보 API 호출.
    반환 dict 키:
        tmp     기온 (°C)
        sky     하늘상태 텍스트
        sky_icon 이모지
        pty     강수형태 텍스트
        pty_icon 이모지
        pop     강수확률 (%)
        pcp     1시간 강수량 (mm) — '강수없음' 문자열일 수 있음
        wsd     풍속 (m/s)
        wind_level  풍속 위험 등급
        vec     풍향 (도)
        vec_str 풍향 텍스트 (북/북동/동 …)
        reh     습도 (%)
        error   오류 메시지 (정상이면 None)
    """
    if not WEATHER_API_KEY:
        return _dummy_weather()

    nx, ny = get_grid(address)
    base_date, base_time = _get_base_time()

    url = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": WEATHER_API_KEY,
        "numOfRows": 100,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        items = data["response"]["body"]["items"]["item"]
            
            # 현재 시각에 가장 가까운 예보 시간 찾기
        now_str = datetime.now(KST).strftime("%H%M")
        times = sorted(set(item["fcstTime"] for item in items))
        nearest = min(times, key=lambda t: abs(int(t) - int(now_str)))
            
            # 해당 시간대 데이터만 필터링
        result = {}
        for item in items:
            if item["fcstTime"] == nearest:
                result[item["category"]] = item["fcstValue"]

        tmp  = float(result.get("TMP", 0))
        sky  = int(result.get("SKY", 1))
        pty  = int(result.get("PTY", 0))
        pop  = result.get("POP", "0")
        pcp  = result.get("PCP", "강수없음")
        wsd  = float(result.get("WSD", 0))
        vec  = float(result.get("VEC", 0))
        reh  = result.get("REH", "0")

        return {
            "tmp":        tmp,
            "sky":        SKY_MAP.get(sky, "알 수 없음"),
            "sky_icon":   SKY_ICON.get(sky, ""),
            "pty":        PTY_MAP.get(pty, "없음"),
            "pty_icon":   PTY_ICON.get(pty, ""),
            "pop":        f"{pop}%",
            "pcp":        pcp,
            "wsd":        wsd,
            "wind_level": wind_level(wsd)[0],
            "wind_safe":  wind_level(wsd)[1],
            "vec":        vec,
            "vec_str":    _vec_to_str(vec),
            "reh":        f"{reh}%",
            "error":      None,
        }

    except Exception as e:
        return {**_dummy_weather(), "error": str(e)}


def _vec_to_str(deg: float) -> str:
    """풍향 각도 → 텍스트 (8방위)"""
    dirs = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]
    return dirs[int((deg + 22.5) / 45) % 8]


def _dummy_weather() -> dict:
    """API 키 없을 때 반환하는 기본값"""
    return {
        "tmp": None, "sky": "—", "sky_icon": "—",
        "pty": "—", "pty_icon": "", "pop": "—",
        "pcp": "—", "wsd": None, "wind_level": "—",
        "wind_safe": "safe", "vec": None, "vec_str": "—",
        "reh": "—", "error": "API 키 없음",
    }