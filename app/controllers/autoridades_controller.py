"""
CRUD autoridades e listagem das mais próximas (para atribuição ao alerta).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_db
from app.schemas.autoridade import (
    AutoridadeCreate,
    AutoridadeUpdate,
    AutoridadeResponse,
)
from app.dependencies.auth import require_autoridade
from app.services.autoridade_service import (
    listar_autoridades,
    obter_autoridade,
    criar_autoridade,
    atualizar_autoridade,
    autoridades_mais_proximas,
)

router = APIRouter(prefix="/autoridades", tags=["Autoridades"])


@router.get("/", response_model=list[AutoridadeResponse])
def listar(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    ativo: bool | None = Query(None),
    tipo: str | None = Query(None),
    id_municipio: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    items = listar_autoridades(db, ativo=ativo, tipo=tipo, id_municipio=id_municipio, skip=skip, limit=limit)
    return [AutoridadeResponse.model_validate(a) for a in items]


@router.get("/proximas", response_model=list[AutoridadeResponse])
def listar_proximas(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    latitude: float = Query(...),
    longitude: float = Query(...),
    tipo: str | None = Query(None),
    limite: int = Query(10, ge=1, le=50),
):
    """Autoridades mais próximas de um ponto (para escolher qual enviar ao alerta)."""
    items = autoridades_mais_proximas(db, latitude=latitude, longitude=longitude, tipo=tipo, limite=limite)
    return [AutoridadeResponse.model_validate(a) for a in items]


@router.get("/{id_autoridade}", response_model=AutoridadeResponse)
def obter(
    id_autoridade: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    auth = obter_autoridade(db, id_autoridade)
    if not auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autoridade não encontrada.")
    return AutoridadeResponse.model_validate(auth)


@router.post("/", response_model=AutoridadeResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: AutoridadeCreate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    return AutoridadeResponse.model_validate(criar_autoridade(db, data.model_dump()))


@router.patch("/{id_autoridade}", response_model=AutoridadeResponse)
def atualizar(
    id_autoridade: int,
    data: AutoridadeUpdate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    auth = atualizar_autoridade(db, id_autoridade, data.model_dump(exclude_unset=True))
    if not auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autoridade não encontrada.")
    return AutoridadeResponse.model_validate(auth)
