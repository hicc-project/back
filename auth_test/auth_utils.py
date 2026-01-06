# auth_utils.py
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta


# bcrypt 알고리즘을 사용하도록 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. 비밀번호를 해시(암호화)하기
def get_password_hash(password: str):
    return pwd_context.hash(password)

# 2. 입력받은 비밀번호와 암호화된 비밀번호 비교하기
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)