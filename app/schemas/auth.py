from pydantic import BaseModel
from typing import Optional


class LoginAutoridadeRequest(BaseModel):
    email: str
    password: str


class LoginCidadaoRequest(BaseModel):
    telefone: Optional[str] = None
    email: Optional[str] = None
    password: str


class RegistroCidadaoRequest(BaseModel):
    nome: Optional[str] = None
    idade: Optional[int] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str  # 'cidadao' | 'autoridade'
    user_id: int


class UserInfo(BaseModel):
    id: int
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    role: str
