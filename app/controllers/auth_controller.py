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
    create_token_cidadao,
    obter_cidadao_para_login,
    register_cidadao,
)
from app.services.cidadao_service import obter_cidadao_por_telefone, obter_cidadao_por_email, obter_cidadao_por_bi

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/autoridade/login", response_model=TokenResponse)
def login_autoridade(data: LoginAutoridadeRequest, db: Session = Depends(get_db)):
    user = authenticate_autoridade(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
    return TokenResponse(**create_token_autoridade(user))


@router.post("/cidadao/login", response_model=TokenResponse)
def login_cidadao(data: LoginCidadaoRequest, db: Session = Depends(get_db)):
    """Login com telefone OU BI (sem palavra-passe). Para usar após terminar sessão."""
    if not data.telefone and not data.bi:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o telefone ou o BI associado à sua conta.",
        )
    cidadao = obter_cidadao_para_login(db, data.telefone, data.bi)
    if not cidadao:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não existe conta com este telefone ou BI. Crie uma conta primeiro.",
        )
    return TokenResponse(**create_token_cidadao(cidadao))


@router.post("/cidadao/logout")
def logout_cidadao():
    """Terminar sessão. O cliente deve apagar o token guardado no dispositivo."""
    return {"message": "Sessão terminada. Apague o token no dispositivo."}


@router.post("/cidadao/registro", response_model=TokenResponse)
def registro_cidadao(data: RegistroCidadaoRequest, db: Session = Depends(get_db)):
    if obter_cidadao_por_telefone(db, data.telefone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone já registado.")
    if obter_cidadao_por_bi(db, data.bi):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BI já registado.")
    if data.email and obter_cidadao_por_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registado.")
    contatos = [
        {"nome": c.nome, "telefone": c.telefone, "email": c.email, "tipo": c.tipo}
        for c in data.contatos_emergencia
    ]
    cidadao = register_cidadao(
        db,
        nome=data.nome,
        data_nascimento=data.data_nascimento,
        telefone=data.telefone,
        bi=data.bi,
        password=data.password,
        contatos_emergencia=contatos,
        email=data.email,
        fotografia_url=data.fotografia_url,
        fotografia_base64=data.fotografia_base64,
        genero=data.genero,
    )
    return TokenResponse(**create_token_cidadao(cidadao))
