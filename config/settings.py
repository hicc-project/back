import os
from dotenv import load_dotenv

load_dotenv()

# ---------- Kakao Local API ----------
KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY", "").strip().strip('"').strip("'")
if not KAKAO_REST_KEY:
    raise RuntimeError("KAKAO_REST_KEY가 없습니다. .env에 KAKAO_REST_KEY=... 설정하세요.")

# ---------- Search center (home) ----------
HOME_LAT = float(os.getenv("HOME_LAT", "37.5477"))
HOME_LNG = float(os.getenv("HOME_LNG", "126.9225"))
RADIUS_M = int(os.getenv("RADIUS_M", "1000"))
CATEGORY_CODE_CAFE = "CE7"
REQUEST_SLEEP_SEC = float(os.getenv("REQUEST_SLEEP_SEC", "0.2"))

# ---------- panel3 cookie (권장: .env로) ----------
PANEL3_COOKIE = os.getenv("PANEL3_COOKIE", "").strip()
if not PANEL3_COOKIE:
    # 처음엔 없어도 실행은 되게 하고, panel3 호출할 때만 에러 내도 됨
    pass

# ---------- HTTP common ----------
HTTP_TIMEOUT_SEC = int(os.getenv("HTTP_TIMEOUT_SEC", "20"))
REQUEST_SLEEP_SEC = float(os.getenv("REQUEST_SLEEP_SEC", "0.2"))
