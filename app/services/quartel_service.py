from sqlalchemy.orm import Session
from app.models.models import Quartel


def listar_quarteis(
    db: Session,
    tipo: str | None = None,
    ativo: bool | None = None,
    nome: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(Quartel)
    if tipo is not None:
        q = q.filter(Quartel.tipo == tipo)
    if ativo is not None:
        q = q.filter(Quartel.ativo == ativo)
    if nome is not None and nome.strip():
        q = q.filter(Quartel.nome.ilike(f"%{nome.strip()}%"))
    return q.order_by(Quartel.nome).offset(skip).limit(limit).all()


def obter_quartel(db: Session, id_quartel: int):
    return db.query(Quartel).filter(Quartel.id == id_quartel).first()


def criar_quartel(db: Session, data: dict):
    quartel = Quartel(**data)
    db.add(quartel)
    db.commit()
    db.refresh(quartel)
    return quartel


def atualizar_quartel(db: Session, id_quartel: int, data: dict):
    quartel = obter_quartel(db, id_quartel)
    if not quartel:
        return None
    for k, v in data.items():
        if hasattr(quartel, k):
            setattr(quartel, k, v)
    db.commit()
    db.refresh(quartel)
    return quartel


def apagar_quartel(db: Session, id_quartel: int) -> bool:
    quartel = obter_quartel(db, id_quartel)
    if not quartel:
        return False
    db.delete(quartel)
    db.commit()
    return True
