"""
Quarteis: CRUD para autoridades (dashboard).
Quartel da polícia, quartel dos bombeiros, quartel de saúde – nome, tipo, latitude, longitude.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_db
from app.schemas.quartel import QuartelCreate, QuartelUpdate, QuartelResponse
from app.dependencies.auth import require_autoridade
from app.services.quartel_service import (
    listar_quarteis,
    obter_quartel,
    criar_quartel,
    atualizar_quartel,
    apagar_quartel,
)

router = APIRouter(prefix="/quarteis", tags=["Quarteis"])

TIPOS_VALIDOS = {"policia", "bombeiros", "saude"}


def _validar_tipo(tipo: str) -> None:
    if tipo and tipo.lower() not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de quartel inválido. Use: {', '.join(TIPOS_VALIDOS)}",
        )


@router.get("/", response_model=list[QuartelResponse])
def listar(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    tipo: str | None = Query(None, description="Filtrar por tipo: policia, bombeiros, saude"),
    ativo: bool | None = Query(None),
    nome: str | None = Query(None, description="Pesquisar quartel pelo nome (parcial)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    if tipo:
        _validar_tipo(tipo)
    items = listar_quarteis(db, tipo=tipo, ativo=ativo, nome=nome, skip=skip, limit=limit)
    return [QuartelResponse.model_validate(q) for q in items]


@router.post("/", response_model=QuartelResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: QuartelCreate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    _validar_tipo(data.tipo)
    return QuartelResponse.model_validate(criar_quartel(db, data.model_dump()))


@router.get("/{id_quartel}", response_model=QuartelResponse)
def obter(
    id_quartel: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    q = obter_quartel(db, id_quartel)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quartel não encontrado.")
    return QuartelResponse.model_validate(q)


@router.patch("/{id_quartel}", response_model=QuartelResponse)
def atualizar(
    id_quartel: int,
    data: QuartelUpdate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    if data.tipo is not None:
        _validar_tipo(data.tipo)
    q = atualizar_quartel(db, id_quartel, data.model_dump(exclude_unset=True))
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quartel não encontrado.")
    return QuartelResponse.model_validate(q)


@router.delete("/{id_quartel}")
def apagar(
    id_quartel: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    if not apagar_quartel(db, id_quartel):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quartel não encontrado.")
    return {"message": "Quartel removido."}
