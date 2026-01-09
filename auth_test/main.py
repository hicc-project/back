from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError

from auth_test import db_mock as db
from auth_test import auth_utils
from auth_test import schemas

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def get_current_user_username(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")


@app.get("/")
def home():
    return {"message": "HICC 카페 찾기 서비스 - 인증 서버"}

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/signup")
def signup(user: schemas.UserRegister):
    if db.find_user(user.username):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    hashed_password = auth_utils.get_password_hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    user_data["favorite_cafes"] = []

    db.save_user(user_data)
    return {"message": f"{user.nickname}님, 가입을 축하합니다!"}


# (선택) JSON 로그인도 계속 유지하고 싶다면
@app.post("/login")
def login(user: schemas.UserLogin):
    found = db.find_user(user.username)
    if not found or not auth_utils.verify_password(user.password, found["password"]):
        raise HTTPException(status_code=401, detail="로그인 실패")

    access_token = auth_utils.create_access_token(data={"sub": found["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


# Swagger Authorize가 사용하는 표준 토큰 발급 엔드포인트
@app.post("/token")
def token(form_data: OAuth2PasswordRequestForm = Depends()):
    found = db.find_user(form_data.username)
    if not found or not auth_utils.verify_password(form_data.password, found["password"]):
        raise HTTPException(status_code=401, detail="로그인 실패")

    access_token = auth_utils.create_access_token(data={"sub": found["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/bookmarks/cafes")
def add_favorite_cafe(cafe_name: str, current_username: str = Depends(get_current_user_username)):
    user = db.find_user(current_username)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if "favorite_cafes" not in user:
        user["favorite_cafes"] = []

    if cafe_name in user["favorite_cafes"]:
        return {"message": f"'{cafe_name}'은(는) 이미 등록된 카페입니다.", "my_favorite_cafes": user["favorite_cafes"]}

    user["favorite_cafes"].append(cafe_name)
    return {"message": f"'{cafe_name}' 카페가 즐겨찾기에 추가되었습니다.", "my_favorite_cafes": user["favorite_cafes"]}


@app.get("/bookmarks/cafes")
def get_my_favorite_cafes(current_username: str = Depends(get_current_user_username)):
    user = db.find_user(current_username)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {"user_nickname": user["nickname"], "favorite_cafes": user.get("favorite_cafes", [])}
