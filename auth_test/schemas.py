from pydantic import BaseModel, Field

class UserRegister(BaseModel):
    username: str = Field(..., description="아이디(식별자)")
    password: str
    nickname: str

class UserLogin(BaseModel):
    username: str = Field(..., description="아이디(식별자)")
    password: str
