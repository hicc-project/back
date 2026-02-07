# parser/cafe_open_hours.py
import re
from datetime import datetime, date, time as dtime, timedelta


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
    '12:00' -> time(12, 0)
    '24:00' -> time(0, 0)  (익일 처리용)
    """
    if not s:
        return None

    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", s)
    if not m:
        return None

    hh = int(m.group(1))
    mi = int(m.group(2))

    if hh == 24 and mi == 0:
        hh = 0
        mi = 0


    if not (0 <= hh <= 23 and 0 <= mi <= 59):
        return None

    return dtime(hh, mi)


def get_today_schedule_from_open_hours(open_hours: dict, now: datetime):
    """
    open_hours(week_from_today 구조)에서 '오늘'에 해당하는 스케줄을 찾는다.
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
                return {
                    "status": "OFF",
                    "open_dt": None,
                    "close_dt": None,
                    "note": f"{day_desc} {d.get('off_days_desc')}",
                }

            # 영업일
            on = d.get("on_days") or {}
            ses = on.get("start_end_time_desc")  # '12:00 ~ 17:00'
            if isinstance(ses, str):
                parts = [p.strip() for p in ses.split("~")]
                if len(parts) == 2:
                    t_open = _parse_hhmm_korean(parts[0])
                    t_close = _parse_hhmm_korean(parts[1])
                    if t_open and t_close:
                        open_dt = datetime.combine(today, t_open)
                        close_dt = datetime.combine(today, t_close)
                        if close_dt <= open_dt:
                            close_dt += timedelta(days=1)
                        return {
                            "status": "OPEN",
                            "open_dt": open_dt,
                            "close_dt": close_dt,
                            "note": f"{day_desc} {ses}",
                        }

            return {
                "status": "OPEN",
                "open_dt": None,
                "close_dt": None,
                "note": f"{day_desc} (시간 파싱 실패)",
            }

    return {"status": None, "open_dt": None, "close_dt": None, "note": None}


def parse_from_panel3(panel: dict) -> dict:
    """
    panel3 JSON에서 필요한 정보만 추출
    """
    out = {
        "detail_opening_hours": None,
        "detail_breaktime": None,
    }

    oh = panel.get("open_hours")
    if isinstance(oh, dict):
        lines = []
        
        week = oh.get("week_from_today", {})
        periods = week.get("week_periods", [])

        for period in periods:
            for d in period.get("days", []):
                day = d.get("day_of_the_week_desc")
                if d.get("off_days_desc"):
                    lines.append(f"{day} 휴무")
                elif "on_days" in d:
                    t = d["on_days"].get("start_end_time_desc")
                    if t:
                        lines.append(f"{day} {t}")

        if lines:
            out["detail_opening_hours"] = " | ".join(lines)

        if out["detail_opening_hours"] is None:
            out["detail_opening_hours"] = oh.get("headline", {}).get("display_text_info")

    return out
