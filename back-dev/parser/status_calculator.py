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
        "today_open_close": None,   
        "today_status_note": None,  
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
        out["today_open_time"] = open_dt.strftime("%H:%M")   
        out["today_close_time"] = close_dt.strftime("%H:%M") 
        out["today_open_close"] = f"{open_dt.strftime('%H:%M')} ~ {close_dt.strftime('%H:%M')}"

        if open_dt <= now < close_dt:
            out["is_open_now"] = True
            out["minutes_to_close"] = int((close_dt - now).total_seconds() // 60)
        else:
            out["is_open_now"] = False
            if now < open_dt:
                out["minutes_to_open"] = int((open_dt - now).total_seconds() // 60)

        return out

    out["is_open_now"] = None
    return out
