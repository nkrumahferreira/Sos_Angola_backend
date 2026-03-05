"""
Províncias e municípios (para formulários e autoridades).
"""
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.schemas.localizacao import ProvinciaResponse, MunicipioResponse
from sqlalchemy.orm import Session
from app.models.models import Provincia, Municipio

router = APIRouter(prefix="/localizacao", tags=["Localização"])


@router.get("/provincias", response_model=list[ProvinciaResponse])
def listar_provincias(db: Session = Depends(get_db), ativo: bool = True):
    items = db.query(Provincia).filter(Provincia.ativo == ativo).order_by(Provincia.nome).all()
    return [ProvinciaResponse.model_validate(p) for p in items]


@router.get("/municipios", response_model=list[MunicipioResponse])
def listar_municipios(
    db: Session = Depends(get_db),
    id_provincia: int | None = Query(None),
    ativo: bool = True,
):
    q = db.query(Municipio).filter(Municipio.ativo == ativo)
    if id_provincia is not None:
        q = q.filter(Municipio.id_provincia == id_provincia)
    items = q.order_by(Municipio.nome).all()
    return [MunicipioResponse.model_validate(m) for m in items]
