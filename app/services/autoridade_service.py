from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import Autoridade


def listar_autoridades(
    db: Session,
    ativo: bool | None = True,
    tipo: str | None = None,
    id_municipio: int | None = None,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(Autoridade)
    if ativo is not None:
        q = q.filter(Autoridade.ativo == ativo)
    if tipo:
        q = q.filter(Autoridade.tipo == tipo)
    if id_municipio is not None:
        q = q.filter(Autoridade.id_municipio == id_municipio)
    return q.offset(skip).limit(limit).all()


def obter_autoridade(db: Session, id_autoridade: int) -> Autoridade | None:
    return db.query(Autoridade).filter(Autoridade.id == id_autoridade).first()


def criar_autoridade(db: Session, data: dict) -> Autoridade:
    auth = Autoridade(**data)
    db.add(auth)
    db.commit()
    db.refresh(auth)
    return auth


def atualizar_autoridade(db: Session, id_autoridade: int, data: dict) -> Autoridade | None:
    auth = obter_autoridade(db, id_autoridade)
    if not auth:
        return None
    for k, v in data.items():
        if hasattr(auth, k):
            setattr(auth, k, v)
    db.commit()
    db.refresh(auth)
    return auth


def autoridades_mais_proximas(
    db: Session,
    latitude: float,
    longitude: float,
    tipo: str | None = None,
    limite: int = 10,
):
    """Retorna autoridades ordenadas por distância (Haversine aproximado)."""
    q = db.query(Autoridade).filter(
        Autoridade.ativo == True,
        Autoridade.latitude.isnot(None),
        Autoridade.longitude.isnot(None),
    )
    if tipo:
        q = q.filter(Autoridade.tipo == tipo)
    todas = q.all()
    # Ordenar por distância euclidiana simples (suficiente para "mais próximos")
    def dist(a):
        return (a.latitude - latitude) ** 2 + (a.longitude - longitude) ** 2
    ordenadas = sorted(todas, key=dist)
    return ordenadas[:limite]
