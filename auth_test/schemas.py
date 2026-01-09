from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)
    nickname: str = Field(min_length=1, max_length=30)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
