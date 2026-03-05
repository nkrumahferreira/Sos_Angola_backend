"""
Autenticação: login autoridades (dashboard) e login/registo cidadão (app).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    LoginAutoridadeRequest,
    LoginCidadaoRequest,
    RegistroCidadaoRequest,
    TokenResponse,
)
from app.services.auth_service import (
    authenticate_autoridade,
    create_token_autoridade,
    authenticate_cidadao,
    create_token_cidadao,
    register_cidadao,
)
from app.services.cidadao_service import obter_cidadao_por_telefone, obter_cidadao_por_email

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/autoridade/login", response_model=TokenResponse)
def login_autoridade(data: LoginAutoridadeRequest, db: Session = Depends(get_db)):
    user = authenticate_autoridade(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
    return TokenResponse(**create_token_autoridade(user))


@router.post("/cidadao/login", response_model=TokenResponse)
def login_cidadao(data: LoginCidadaoRequest, db: Session = Depends(get_db)):
    if not data.telefone and not data.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe telefone ou email.")
    cidadao = authenticate_cidadao(db, data.telefone, data.email, data.password)
    if not cidadao:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
    return TokenResponse(**create_token_cidadao(cidadao))


@router.post("/cidadao/registro", response_model=TokenResponse)
def registro_cidadao(data: RegistroCidadaoRequest, db: Session = Depends(get_db)):
    if not data.telefone and not data.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe telefone ou email.")
    if data.telefone and obter_cidadao_por_telefone(db, data.telefone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone já registado.")
    if data.email and obter_cidadao_por_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registado.")
    cidadao = register_cidadao(
        db,
        nome=data.nome,
        idade=data.idade,
        telefone=data.telefone,
        email=data.email,
        password=data.password,
    )
    return TokenResponse(**create_token_cidadao(cidadao))
