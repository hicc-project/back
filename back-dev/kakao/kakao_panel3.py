import requests

from config.settings import PANEL3_COOKIE, HTTP_TIMEOUT_SEC


PANEL3_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "appversion": "6.6.0",
    "origin": "https://place.map.kakao.com",
    "pf": "PC",
    "referer": "https://place.map.kakao.com/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}

if PANEL3_COOKIE:
    PANEL3_HEADERS["Cookie"] = PANEL3_COOKIE

def fetch_panel3(place_id: str) -> dict:
    url = f"https://place-api.map.kakao.com/places/panel3/{place_id}"
    r = requests.get(url, headers=PANEL3_HEADERS, timeout=(3,5))

    # 쿠키 만료 등 디버그 도움
    if r.status_code != 200:
        raise requests.HTTPError(f"{r.status_code} {r.text[:200]}")

    return r.json()
