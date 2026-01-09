# 임시 데이터 저장소 (메모리)
users_db = []

def save_user(user_data):
    users_db.append(user_data)
    return True

def find_user(username: str):
    return next((user for user in users_db if user["username"] == username), None)
