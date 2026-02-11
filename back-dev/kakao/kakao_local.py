import time
import requests



def kakao_search_category(lat: float, lng: float, radius: int, category_code: str,
                          size: int = 15, max_pages: int = 10):
    from config.settings import KAKAO_REST_KEY
    
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