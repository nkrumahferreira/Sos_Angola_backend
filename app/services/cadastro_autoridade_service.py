"""
Service para Cadastro de Autoridades (pessoas vinculadas a um quartel).
"""
from sqlalchemy.orm import Session, joinedload
from app.models.models import CadastroAutoridade, Quartel
from app.utils.password_utils import hash_password


def listar_cadastros(
    db: Session,
    tipo: str | None = None,
    id_quartel: int | None = None,
    ativo: bool | None = None,
    nome: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(CadastroAutoridade).options(joinedload(CadastroAutoridade.quartel))
    if tipo is not None:
        q = q.filter(CadastroAutoridade.tipo == tipo)
    if id_quartel is not None:
        q = q.filter(CadastroAutoridade.id_quartel == id_quartel)
    if ativo is not None:
        q = q.filter(CadastroAutoridade.ativo == ativo)
    if nome is not None and nome.strip():
        q = q.filter(CadastroAutoridade.nome.ilike(f"%{nome.strip()}%"))
    return q.order_by(CadastroAutoridade.nome).offset(skip).limit(limit).all()


def obter_cadastro(db: Session, id_cadastro: int):
    return (
        db.query(CadastroAutoridade)
        .options(joinedload(CadastroAutoridade.quartel))
        .filter(CadastroAutoridade.id == id_cadastro)
        .first()
    )


def obter_por_email(db: Session, email: str):
    return db.query(CadastroAutoridade).filter(CadastroAutoridade.email == email.strip().lower()).first()


def criar_cadastro(db: Session, data: dict):
    payload = {k: v for k, v in data.items() if k != "senha"}
    if "senha" in data and data["senha"]:
        payload["password_hash"] = hash_password(data["senha"])
    payload["email"] = payload.get("email", "").strip().lower()
    cadastro = CadastroAutoridade(**payload)
    db.add(cadastro)
    db.commit()
    db.refresh(cadastro)
    db.refresh(cadastro, ["quartel"])
    return cadastro


def atualizar_cadastro(db: Session, id_cadastro: int, data: dict):
    cadastro = obter_cadastro(db, id_cadastro)
    if not cadastro:
        return None
    payload = data.copy()
    if "senha" in payload and payload["senha"]:
        payload["password_hash"] = hash_password(payload.pop("senha"))
    elif "senha" in payload:
        payload.pop("senha")
    if "email" in payload and payload["email"]:
        payload["email"] = payload["email"].strip().lower()
    for k, v in payload.items():
        if hasattr(cadastro, k):
            setattr(cadastro, k, v)
    db.commit()
    db.refresh(cadastro)
    db.refresh(cadastro, ["quartel"])
    return cadastro


def apagar_cadastro(db: Session, id_cadastro: int) -> bool:
    cadastro = obter_cadastro(db, id_cadastro)
    if not cadastro:
        return False
    db.delete(cadastro)
    db.commit()
    return True
