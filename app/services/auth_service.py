from sqlalchemy.orm import Session
from app.models.models import UsuarioAutoridade, Cidadao, ContatoEmergencia
from app.utils.password_utils import verify_password, hash_password
from app.utils.jwt_utils import create_access_token
from app.config import settings
from datetime import date


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


def obter_cidadao_para_login(db: Session, telefone: str | None, bi: str | None) -> Cidadao | None:
    """Obtém cidadão por telefone ou BI (login sem palavra-passe, para reentrada no app)."""
    if not telefone and not bi:
        return None
    q = db.query(Cidadao).filter(Cidadao.ativo == True)
    if telefone:
        return q.filter(Cidadao.telefone == telefone).first()
    if bi:
        return q.filter(Cidadao.bi == (bi.strip().upper() if bi else None)).first()
    return None


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
    nome: str,
    data_nascimento: date,
    telefone: str,
    bi: str,
    password: str,
    contatos_emergencia: list[dict],  # [{"nome": str, "telefone": str, "email": str|None, "tipo": str|None}, ...]
    email: str | None = None,
    fotografia_url: str | None = None,
    fotografia_base64: str | None = None,
    genero: str | None = None,
) -> Cidadao:
    cidadao = Cidadao(
        nome=nome,
        data_nascimento=data_nascimento,
        telefone=telefone,
        bi=bi,
        password_hash=hash_password(password),
        email=email,
        fotografia_url=fotografia_url,
        fotografia_base64=fotografia_base64,
        genero=genero,
    )
    db.add(cidadao)
    db.flush()  # para obter cidadao.id antes de inserir contatos
    for c in contatos_emergencia:
        contato = ContatoEmergencia(
            id_cidadao=cidadao.id,
            nome=c["nome"],
            telefone=c["telefone"],
            email=c.get("email"),
            tipo=c.get("tipo"),
        )
        db.add(contato)
    db.commit()
    db.refresh(cidadao)
    return cidadao
