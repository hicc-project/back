from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from pydantic import BaseModel

from auth_test import db_mock as db
from auth_test import auth_utils
from auth_test import schemas

app = FastAPI(title="HICC Auth Server", version="1.0.0")

# Swagger의 Authorize(자물쇠)가 토큰을 받을 엔드포인트를 /token으로 지정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    """
    Authorization: Bearer <token> 에서 토큰을 꺼내 검증하고,
    payload의 sub(email)을 반환한다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            auth_utils.SECRET_KEY,
            algorithms=[auth_utils.ALGORITHM],
        )
        email = payload.get("sub")
        if not email:
            raise credentials_exception

        # 토큰의 sub에 해당하는 사용자가 실제 존재하는지도 확인(안전장치)
        if not db.find_user(email):
            raise credentials_exception

        return email

    except JWTError:
        raise credentials_exception


@app.get("/")
def home():
    return {"message": "HICC 카페 찾기 서비스 - 인증 서버"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user: schemas.UserRegister):
    # 이메일 중복 체크
    if db.find_user(user.email):
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    hashed_password = auth_utils.get_password_hash(user.password)

    user_data = user.dict()
    user_data["password"] = hashed_password
    user_data["favorite_cafes"] = []

    db.save_user(user_data)
    return {"message": f"{user.nickname}님, 가입을 축하합니다!"}


# ✅ 프론트/일반 클라이언트용: JSON 로그인(기존 방식 유지)
@app.post("/login", response_model=TokenResponse)
def login_json(user: schemas.UserLogin):
    found = db.find_user(user.email)
    if not found or not auth_utils.verify_password(user.password, found["password"]):
        raise HTTPException(status_code=401, detail="로그인 실패")

    access_token = auth_utils.create_access_token(data={"sub": found["email"]})
    return {"access_token": access_token, "token_type": "bearer"}


# ✅ Swagger Authorize용: OAuth2 Password Flow(Form) 로그인
# Authorize 팝업의 username 칸에 "이메일"을 넣으면 됨
@app.post("/token", response_model=TokenResponse)
def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    found = db.find_user(form_data.username)  # username 자리에 이메일을 넣어 사용
    if not found or not auth_utils.verify_password(form_data.password, found["password"]):
        raise HTTPException(status_code=401, detail="로그인 실패")

    access_token = auth_utils.create_access_token(data={"sub": found["email"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/bookmarks/cafes")
def add_favorite_cafe(
    cafe_name: str = Query(..., min_length=1),
    current_user_email: str = Depends(get_current_user_email),
):
    user = db.find_user(current_user_email)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user.setdefault("favorite_cafes", [])

    if cafe_name in user["favorite_cafes"]:
        return {
            "message": f"'{cafe_name}'은(는) 이미 즐겨찾기에 등록된 카페입니다.",
            "my_favorite_cafes": user["favorite_cafes"],
        }

    user["favorite_cafes"].append(cafe_name)

    # ⚠️ db_mock이 append만 하는 구조면 중복 유저가 생길 수 있음.
    # db_mock.save_user를 upsert(있으면 업데이트)로 만들어두는 걸 추천.
    db.save_user(user)

    return {
        "message": f"'{cafe_name}' 카페가 즐겨찾기에 추가되었습니다.",
        "my_favorite_cafes": user["favorite_cafes"],
    }


@app.get("/bookmarks/cafes")
def get_my_favorite_cafes(current_user_email: str = Depends(get_current_user_email)):
    user = db.find_user(current_user_email)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {
        "user_nickname": user.get("nickname"),
        "favorite_cafes": user.get("favorite_cafes", []),
    }
