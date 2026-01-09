# 임시 데이터 저장소 (실제 DB 대신)
users_db = []

def save_user(user_data: dict):
    """
    upsert: 같은 email이 있으면 업데이트, 없으면 추가
    """
    email = user_data.get("email")
    if not email:
        return False

    for i, user in enumerate(users_db):
        if user.get("email") == email:
            users_db[i] = user_data
            return True

    users_db.append(user_data)
    return True


def find_user(email: str):
    return next((user for user in users_db if user.get("email") == email), None)
