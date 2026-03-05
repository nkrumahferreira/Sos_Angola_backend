"""
Notícias: CRUD para autoridades (dashboard); listagem publicada para app.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_db
from app.schemas.noticia import NoticiaCreate, NoticiaUpdate, NoticiaResponse
from app.dependencies.auth import require_autoridade, get_current_user_id_optional
from app.services.noticia_service import (
    listar_noticias,
    obter_noticia,
    criar_noticia,
    atualizar_noticia,
    apagar_noticia,
)

router = APIRouter(prefix="/noticias", tags=["Notícias"])


@router.get("/", response_model=list[NoticiaResponse])
def listar_publicadas(
    db=Depends(get_db),
    categoria: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Público / app: lista notícias publicadas (primeiros socorros, etc.)."""
    items = listar_noticias(db, publicada=True, categoria=categoria, skip=skip, limit=limit)
    return [NoticiaResponse.model_validate(n) for n in items]


@router.get("/{id_noticia}", response_model=NoticiaResponse)
def obter(id_noticia: int, db=Depends(get_db)):
    n = obter_noticia(db, id_noticia)
    if not n or not n.publicada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada.")
    return NoticiaResponse.model_validate(n)


# --- Dashboard autoridades (CRUD) ---
@router.get("/admin/", response_model=list[NoticiaResponse])
def listar_todas(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    publicada: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    items = listar_noticias(db, publicada=publicada, skip=skip, limit=limit)
    return [NoticiaResponse.model_validate(n) for n in items]


@router.post("/admin/", response_model=NoticiaResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: NoticiaCreate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    return NoticiaResponse.model_validate(criar_noticia(db, data.model_dump()))


@router.get("/admin/{id_noticia}", response_model=NoticiaResponse)
def obter_admin(
  id_noticia: int,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    n = obter_noticia(db, id_noticia)
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada.")
    return NoticiaResponse.model_validate(n)


@router.patch("/admin/{id_noticia}", response_model=NoticiaResponse)
def atualizar(
  id_noticia: int,
  data: NoticiaUpdate,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    n = atualizar_noticia(db, id_noticia, data.model_dump(exclude_unset=True))
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada.")
    return NoticiaResponse.model_validate(n)


@router.delete("/admin/{id_noticia}")
def apagar(
  id_noticia: int,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    if not apagar_noticia(db, id_noticia):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada.")
    return {"message": "Notícia removida."}
