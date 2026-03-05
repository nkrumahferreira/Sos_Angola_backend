from sqlalchemy.orm import Session
from app.models.models import Noticia


def listar_noticias(
    db: Session,
    publicada: bool | None = True,
    categoria: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    q = db.query(Noticia)
    if publicada is not None:
        q = q.filter(Noticia.publicada == publicada)
    if categoria:
        q = q.filter(Noticia.categoria == categoria)
    return q.order_by(Noticia.created_at.desc()).offset(skip).limit(limit).all()


def obter_noticia(db: Session, id_noticia: int) -> Noticia | None:
    return db.query(Noticia).filter(Noticia.id == id_noticia).first()


def criar_noticia(db: Session, data: dict) -> Noticia:
    n = Noticia(**data)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def atualizar_noticia(db: Session, id_noticia: int, data: dict) -> Noticia | None:
    n = obter_noticia(db, id_noticia)
    if not n:
        return None
    for k, v in data.items():
        if hasattr(n, k):
            setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return n


def apagar_noticia(db: Session, id_noticia: int) -> bool:
    n = obter_noticia(db, id_noticia)
    if not n:
        return False
    db.delete(n)
    db.commit()
    return True
