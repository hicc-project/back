import os
import time
import requests
import pandas as pd
import re
from dotenv import load_dotenv
from datetime import datetime, date, time as dtime, timedelta

# =========================
# 1) 환경변수 로드 (Kakao Local API)
# =========================
load_dotenv()
KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY", "").strip().strip('"').strip("'")
if not KAKAO_REST_KEY:
    raise RuntimeError("KAKAO_REST_KEY가 없습니다. .env 파일에 KAKAO_REST_KEY=... 를 넣어주세요.")

# =========================
# 2) 집 좌표/반경
# =========================
HOME_LAT = 37.5499294
HOME_LNG = 126.8379387
RADIUS_M = 1000

# =========================
# 3) Kakao Local API: 카테고리 검색 (카페=CE7)
# =========================
def kakao_search_category(lat: float, lng: float, radius: int, category_code: str,
                          size: int = 15, max_pages: int = 10):
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

    params_base = {
        "category_group_code": category_code,
        "y": lat,
        "x": lng,
        "radius": radius,
        "sort": "distance",
        "size": size,
    }

    all_docs = []
    for page in range(1, max_pages + 1):
        params = dict(params_base)
        params["page"] = page

        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        docs = data.get("documents", [])
        all_docs.extend(docs)

        if data.get("meta", {}).get("is_end", True):
            break

        time.sleep(0.2)  # 과호출 방지

    return all_docs

# =========================
# 4) place-api panel3: 쿠키 기반 요청
# =========================
# ✅ 여기에 Copy as cURL 에서 -b '...' 안의 문자열 "전체"를 그대로 붙여넣기
PANEL3_COOKIE = (
    "webid=98dc7140f930447fb57166dc2437c394; webid_ts=1713861174173; kd_lang=ko; _clck=7hlft0%5E2%5Eg21%5E0%5E2181; _kau=xxxxxxxxxxxxxxxxxxxxxxxx; _kdt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx.yyyyy; _T_ANO=zzzzzzzzzzzzzzzzzz"
)

PANEL3_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "appversion": "6.6.0",
    "origin": "https://place.map.kakao.com",
    "pf": "PC",
    "referer": "https://place.map.kakao.com/",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "priority": "u=1, i",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",

    # ✅ 대문자 Cookie 권장
    "Cookie": PANEL3_COOKIE,
}

def fetch_panel3(place_id: str) -> dict:
    url = f"https://place-api.map.kakao.com/places/panel3/{place_id}"
    r = requests.get(url, headers=PANEL3_HEADERS, timeout=20)

    # 쿠키 만료 등 디버그 도움
    if r.status_code != 200:
        raise requests.HTTPError(f"{r.status_code} {r.text[:200]}")

    return r.json()

def _parse_mmdd_from_desc(day_desc: str, year: int) -> date | None:
    """
    '일(12/28)' 같은 문자열에서 12/28을 뽑아서 date(year, 12, 28)로 변환
    """
    if not day_desc:
        return None
    m = re.search(r"\((\d{1,2})/(\d{1,2})\)", day_desc)
    if not m:
        return None
    mm = int(m.group(1))
    dd = int(m.group(2))
    return date(year, mm, dd)

def _parse_hhmm_korean(s: str) -> dtime | None:
    """
    '12:00' -> time(12,0)
    """
    if not s:
        return None
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", s)
    if not m:
        return None
    hh = int(m.group(1))
    mi = int(m.group(2))
    return dtime(hh, mi)

def get_today_schedule_from_open_hours(open_hours: dict, now: datetime):
    """
    open_hours(week_from_today 구조)에서 '오늘'에 해당하는 스케줄을 찾는다.
    반환:
      - status: "OFF" | "OPEN"
      - open_dt, close_dt: datetime or None
      - note: str (휴무/시간 문자열 등)
    """
    if not isinstance(open_hours, dict):
        return {"status": None, "open_dt": None, "close_dt": None, "note": None}

    today = now.date()
    year = today.year

    week = open_hours.get("week_from_today", {})
    periods = week.get("week_periods", []) or []

    for period in periods:
        for d in (period.get("days", []) or []):
            day_desc = d.get("day_of_the_week_desc")
            d_date = _parse_mmdd_from_desc(day_desc, year)
            if d_date != today:
                continue

            # 휴무
            if d.get("off_days_desc"):
                return {"status": "OFF", "open_dt": None, "close_dt": None, "note": f"{day_desc} {d.get('off_days_desc')}"}

            # 영업일
            on = d.get("on_days") or {}
            ses = on.get("start_end_time_desc")  # 예: '12:00 ~ 17:00'
            if isinstance(ses, str):
                parts = [p.strip() for p in ses.split("~")]
                if len(parts) == 2:
                    t_open = _parse_hhmm_korean(parts[0])
                    t_close = _parse_hhmm_korean(parts[1])
                    if t_open and t_close:
                        open_dt = datetime.combine(today, t_open)
                        close_dt = datetime.combine(today, t_close)

                        # 혹시 자정 넘어가는 영업(예: 18:00~02:00) 대비
                        if close_dt <= open_dt:
                            close_dt += timedelta(days=1)

                        return {"status": "OPEN", "open_dt": open_dt, "close_dt": close_dt, "note": f"{day_desc} {ses}"}

            # 시간 파싱 실패 fallback
            return {"status": "OPEN", "open_dt": None, "close_dt": None, "note": f"{day_desc} (시간 파싱 실패)"}

    # 오늘 항목 자체가 없음
    return {"status": None, "open_dt": None, "close_dt": None, "note": None}

def compute_open_now_and_remaining(panel: dict, now: datetime):
    """
    panel3 JSON에서 open_hours를 읽어
    is_open_now, minutes_to_close, minutes_to_open를 계산
    """
    out = {
        "is_open_now": None,
        "minutes_to_close": None,
        "minutes_to_open": None,
        "today_open_close": None,   # '12:00 ~ 17:00' 같은 표시용
        "today_status_note": None,  # '일(12/28) 휴무' 같은 표시용
    }

    oh = panel.get("open_hours")
    info = get_today_schedule_from_open_hours(oh, now)

    out["today_status_note"] = info.get("note")

    if info["status"] == "OFF":
        out["is_open_now"] = False
        return out

    if info["status"] == "OPEN" and info["open_dt"] and info["close_dt"]:
        open_dt = info["open_dt"]
        close_dt = info["close_dt"]
        out["today_open_close"] = f"{open_dt.strftime('%H:%M')} ~ {close_dt.strftime('%H:%M')}"

        if open_dt <= now < close_dt:
            out["is_open_now"] = True
            out["minutes_to_close"] = int((close_dt - now).total_seconds() // 60)
        else:
            out["is_open_now"] = False
            if now < open_dt:
                out["minutes_to_open"] = int((open_dt - now).total_seconds() // 60)
            # now >= close_dt 면 오늘은 영업 종료(내일 정보는 open_hours에 있을 수도 있으니 원하면 확장 가능)

        return out

    # 오늘 정보가 없거나 시간 파싱 실패
    out["is_open_now"] = None
    return out

# =========================
# 5) panel3 파싱 (open_hours 중심)
# =========================
def parse_from_panel3(panel: dict) -> dict:
    out = {
        "detail_opening_hours": None,
        "detail_breaktime": None,
        "detail_holiday": None,
        "detail_rating": None,
        "detail_review_cnt": None,
    }

    # ---- 리뷰 ----
    review = panel.get("kakaomap_review") or {}
    if isinstance(review, dict):
        out["detail_rating"] = review.get("score")
        out["detail_review_cnt"] = review.get("count") or review.get("review_count")

    # ---- 영업시간 (⭐ 핵심 수정 ⭐) ----
    oh = panel.get("open_hours")
    if isinstance(oh, dict):

        lines = []

        # 휴무 요약
        off_desc = oh.get("headline_addition", {}).get("current_off_day_desc")
        if off_desc:
            out["detail_holiday"] = off_desc

        # 주간 상세
        week = oh.get("week_from_today", {})
        periods = week.get("week_periods", [])

        for period in periods:
            for d in period.get("days", []):
                day = d.get("day_of_the_week_desc")
                if "off_days_desc" in d:
                    lines.append(f"{day} 휴무")
                elif "on_days" in d:
                    t = d["on_days"].get("start_end_time_desc")
                    if t:
                        lines.append(f"{day} {t}")

        if lines:
            out["detail_opening_hours"] = " | ".join(lines)

        # fallback: headline
        if out["detail_opening_hours"] is None:
            out["detail_opening_hours"] = oh.get("headline", {}).get("display_text_info")

    return out


# =========================
# 6) df에 상세정보 붙이기
# =========================
def enrich_df_with_details(df: pd.DataFrame, sleep_sec: float = 0.2) -> pd.DataFrame:
    details = []
    now = datetime.now()

    for i, row in df.iterrows():
        pid = str(row["kakao_id"])
        name = row.get("name")

        try:
            panel = fetch_panel3(pid)
            d = parse_from_panel3(panel)
            live = compute_open_now_and_remaining(panel, now)
            d.update(live)
        except Exception as e:
            print(f"[{i}] FAIL {name} ({pid}) | {e}")
            d = {
                "detail_opening_hours": None,
                "detail_breaktime": None,
                "detail_holiday": None,
                "detail_rating": None,
                "detail_review_cnt": None,
            }

        details.append(d)
        time.sleep(sleep_sec)

    return pd.concat([df.reset_index(drop=True), pd.DataFrame(details)], axis=1)

# =========================
# 7) main
# =========================
def main():
    docs = kakao_search_category(
        lat=HOME_LAT,
        lng=HOME_LNG,
        radius=RADIUS_M,
        category_code="CE7",
        size=15,
        max_pages=10
    )

    rows = []
    for d in docs:
        rows.append({
            "kakao_id": d.get("id"),
            "name": d.get("place_name"),
            "address": d.get("address_name"),
            "road_address": d.get("road_address_name"),
            "phone": d.get("phone"),
            "place_url": d.get("place_url"),
            "lat": float(d.get("y")) if d.get("y") else None,
            "lng": float(d.get("x")) if d.get("x") else None,
            "distance_m": int(d.get("distance")) if d.get("distance") else None,
        })

    df = pd.DataFrame(rows).drop_duplicates(subset=["kakao_id"]).reset_index(drop=True)

    print(f"총 {len(df)}개 카페 수집 완료 (반경 {RADIUS_M}m)")
    print(df[["name", "distance_m", "road_address"]].head(10).to_string(index=False))

    print("\n상세(panel3) 정보 수집 중... (쿠키 기반 requests)")
    df = enrich_df_with_details(df, sleep_sec=0.2)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"nearby_home_cafes_1km_kakao_with_details_{ts}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\nCSV 저장 완료: {out_csv}")

if __name__ == "__main__":
    main()