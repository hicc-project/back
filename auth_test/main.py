from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from auth_test import db_mock as db
from auth_test import auth_utils
from auth_test import schemas

app = FastAPI()

# 토큰 추출 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 현재 로그인한 사용자 확인 함수
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

@app.get("/")
def home():
    return {"message": "HICC 카페 찾기 서비스 - 인증 서버"}

@app.post("/signup")
def signup(user: schemas.UserRegister):
    if db.find_user(user.email):
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")
    
    hashed_password = auth_utils.get_password_hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    user_data["favorite_cafes"] = [] # 'bookmarks' 대신 'favorite_cafes'로 명칭 변경
    
    db.save_user(user_data)
    return {"message": f"{user.nickname}님, 가입을 축하합니다!"}

@app.post("/login")
def login(user: schemas.UserLogin):
    found = db.find_user(user.email)
    if not found or not auth_utils.verify_password(user.password, found["password"]):
        raise HTTPException(status_code=401, detail="로그인 실패")
    
    access_token = auth_utils.create_access_token(data={"sub": found["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

# [수정] 카페 즐겨찾기 등록 API
@app.post("/bookmarks/cafes")
def add_favorite_cafe(cafe_name: str, current_user_email: str = Depends(get_current_user)):
    user = db.find_user(current_user_email)
    
    # 사용자 데이터에 즐겨찾기 리스트가 없으면 생성
    if "favorite_cafes" not in user:
        user["favorite_cafes"] = []
    
    # 중복 추가 방지 로직 (선택 사항)
    if cafe_name in user["favorite_cafes"]:
        return {"message": f"'{cafe_name}'은(는) 이미 즐겨찾기에 등록된 카페입니다."}
    
    user["favorite_cafes"].append(cafe_name)
    return {
        "message": f"'{cafe_name}' 카페가 즐겨찾기에 추가되었습니다.",
        "my_favorite_cafes": user["favorite_cafes"]
    }

# [수정] 내 즐겨찾기 카페 목록 보기 API
@app.get("/bookmarks/cafes")
def get_my_favorite_cafes(current_user_email: str = Depends(get_current_user)):
    user = db.find_user(current_user_email)
    return {
        "user_nickname": user["nickname"],
        "favorite_cafes": user.get("favorite_cafes", [])
    }