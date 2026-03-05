from sqlalchemy.orm import Session
from app.models.models import UsuarioAutoridade, Cidadao
from app.utils.password_utils import verify_password, hash_password
from app.utils.jwt_utils import create_access_token
from app.config import settings


def authenticate_autoridade(db: Session, email: str, password: str) -> UsuarioAutoridade | None:
    user = db.query(UsuarioAutoridade).filter(
        UsuarioAutoridade.email == email,
        UsuarioAutoridade.ativo == True,
    ).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_token_autoridade(user: UsuarioAutoridade) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": "autoridade", "email": user.email},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": "autoridade",
        "user_id": user.id,
    }


def authenticate_cidadao(db: Session, telefone: str | None, email: str | None, password: str) -> Cidadao | None:
    if not telefone and not email:
        return None
    q = db.query(Cidadao).filter(Cidadao.ativo == True)
    if telefone:
        cidadao = q.filter(Cidadao.telefone == telefone).first()
    else:
        cidadao = q.filter(Cidadao.email == email).first()
    if not cidadao or not cidadao.password_hash or not verify_password(password, cidadao.password_hash):
        return None
    return cidadao


def create_token_cidadao(cidadao: Cidadao) -> dict:
    token = create_access_token(
        subject=cidadao.id,
        extra_claims={"role": "cidadao"},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": "cidadao",
        "user_id": cidadao.id,
    }


def register_cidadao(
    db: Session,
    nome: str | None,
    idade: int | None,
    telefone: str | None,
    email: str | None,
    password: str,
) -> Cidadao:
    cidadao = Cidadao(
        nome=nome,
        idade=idade,
        telefone=telefone,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(cidadao)
    db.commit()
    db.refresh(cidadao)
    return cidadao
