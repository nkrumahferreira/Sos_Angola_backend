from sqlalchemy.orm import Session
from app.models.models import PrimeiroSocorro


def listar_primeiros_socorros(
    db: Session,
    ativo: bool | None = True,
    categoria: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PrimeiroSocorro]:
    q = db.query(PrimeiroSocorro)
    if ativo is not None:
        q = q.filter(PrimeiroSocorro.ativo == ativo)
    if categoria:
        q = q.filter(PrimeiroSocorro.categoria == categoria)
    return q.order_by(PrimeiroSocorro.ordem.asc(), PrimeiroSocorro.created_at.desc()).offset(skip).limit(limit).all()


def obter_primeiro_socorro(db: Session, id_ps: int) -> PrimeiroSocorro | None:
    return db.query(PrimeiroSocorro).filter(PrimeiroSocorro.id == id_ps).first()


def criar_primeiro_socorro(db: Session, data: dict) -> PrimeiroSocorro:
    ps = PrimeiroSocorro(**data)
    db.add(ps)
    db.commit()
    db.refresh(ps)
    return ps


def atualizar_primeiro_socorro(db: Session, id_ps: int, data: dict) -> PrimeiroSocorro | None:
    ps = obter_primeiro_socorro(db, id_ps)
    if not ps:
        return None
    for k, v in data.items():
        if hasattr(ps, k):
            setattr(ps, k, v)
    db.commit()
    db.refresh(ps)
    return ps


def apagar_primeiro_socorro(db: Session, id_ps: int) -> bool:
    ps = obter_primeiro_socorro(db, id_ps)
    if not ps:
        return False
    db.delete(ps)
    db.commit()
    return True
