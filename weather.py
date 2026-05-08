"""
weather.py — 기상청 날씨 자동 추출
공공데이터포털(data.go.kr)에서 '기상청_단기예보' API 키 발급 필요
.env에 WEATHER_API_KEY=발급받은키 추가
"""
import os, requests
from dotenv import load_dotenv
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# 주요 도시별 기상청 격자 좌표
GRID_MAP = {
    "서울": (60, 127), "부산": (98, 76),  "인천": (55, 124),
    "대구": (89, 90),  "광주": (58, 74),  "대전": (67, 100),
    "울산": (102, 84), "수원": (60, 121), "창원": (90, 77),
    "고양": (57, 128), "성남": (62, 123), "청주": (69, 106),
    "전주": (63, 89),  "천안": (63, 110), "안양": (59, 123),
}


def get_grid(address: str) -> tuple:
    for city, grid in GRID_MAP.items():
        if city in address:
            return grid
    return (60, 127)  # 기본: 서울


def fetch_weather(address: str, date: str) -> dict:
    """
    Args:
        address: 현장 주소 (예: "서울시 강남구")
        date: "YYYYMMDD" 형식
    Returns:
        날씨 딕셔너리
    """
    if not WEATHER_API_KEY:
        return {
            "available": False,
            "message": (
                "⚠️ 날씨 자동 추출을 사용하려면 .env에 WEATHER_API_KEY를 추가하세요.\n"
                "   공공데이터포털(data.go.kr) → '기상청_단기예보' 검색 → API 키 발급"
            )
        }
    try:
        nx, ny = get_grid(address)
        url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        params = {
            "serviceKey": WEATHER_API_KEY,
            "numOfRows":  300,
            "pageNo":     1,
            "dataType":   "JSON",
            "base_date":  date,
            "base_time":  "0500",
            "nx": nx, "ny": ny,
        }
        resp  = requests.get(url, params=params, timeout=5)
        items = resp.json()["response"]["body"]["items"]["item"]

        temps, winds, hums = [], [], []
        max_wind, peak_time = 0, ""

        for item in items:
            cat, val, t = item["category"], item["fcstValue"], item["fcstTime"]
            try:
                if cat == "TMP":  temps.append(float(val))
                if cat == "WSD":
                    w = float(val)
                    winds.append(w)
                    if w > max_wind:
                        max_wind, peak_time = w, t
                if cat == "REH":  hums.append(float(val))
            except: pass

        return {
            "available":  True,
            "temp_avg":   f"{sum(temps)/len(temps):.1f}°C" if temps else "-",
            "temp_max":   f"{max(temps):.1f}°C"            if temps else "-",
            "humidity":   f"{sum(hums)/len(hums):.0f}%"   if hums  else "-",
            "wind_speed": f"{sum(winds)/len(winds):.1f}m/s" if winds else "-",
            "wind_max":   f"{max_wind:.1f}m/s"             if winds else "-",
            "peak_time":  f"{peak_time[:2]}:{peak_time[2:]}" if peak_time else "-",
        }
    except Exception as e:
        return {"available": False, "message": f"날씨 API 오류: {e}"}
