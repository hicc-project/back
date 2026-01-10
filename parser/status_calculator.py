from datetime import datetime
from parser.cafe_open_hours import get_today_schedule_from_open_hours

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
        "today_open_time": None,
        "today_close_time": None,
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
        out["today_open_time"] = open_dt.strftime("%H:%M")   # ✅ 추가
        out["today_close_time"] = close_dt.strftime("%H:%M") # ✅ 추가
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
