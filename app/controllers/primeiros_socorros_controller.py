"""
Primeiros Socorros: CRUD para autoridades (dashboard); listagem ativa para app (vídeos, imagens, instruções).
Imagem = upload (file); vídeo = URL (ex.: YouTube).
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile

from app.config import settings
from app.database import get_db
from app.schemas.primeiro_socorro import (
    PrimeiroSocorroUpdate,
    PrimeiroSocorroResponse,
)
from app.dependencies.auth import require_autoridade
from app.services.primeiro_socorro_service import (
    listar_primeiros_socorros,
    obter_primeiro_socorro,
    criar_primeiro_socorro,
    atualizar_primeiro_socorro,
    apagar_primeiro_socorro,
)

router = APIRouter(prefix="/primeiros-socorros", tags=["Primeiros Socorros"])

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
MAX_IMAGE_SIZE_MB = 10


@router.get("/", response_model=list[PrimeiroSocorroResponse])
def listar_ativos(
    db=Depends(get_db),
    categoria: str | None = Query(None, description="Filtrar por categoria"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """Público / app: lista primeiros socorros ativos (para a tela do utilizador)."""
    items = listar_primeiros_socorros(db, ativo=True, categoria=categoria, skip=skip, limit=limit)
    return [PrimeiroSocorroResponse.model_validate(x) for x in items]


@router.get("/{id_ps}", response_model=PrimeiroSocorroResponse)
def obter(id_ps: int, db=Depends(get_db)):
    """Público / app: obtém um item de primeiros socorros por ID."""
    ps = obter_primeiro_socorro(db, id_ps)
    if not ps or not ps.ativo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primeiros socorros não encontrados.")
    return PrimeiroSocorroResponse.model_validate(ps)


# --- Dashboard autoridades (CRUD) ---
@router.get("/admin/", response_model=list[PrimeiroSocorroResponse])
def listar_todos(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    ativo: bool | None = Query(None),
    categoria: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """Autoridade: lista todos os itens (para gestão)."""
    items = listar_primeiros_socorros(db, ativo=ativo, categoria=categoria, skip=skip, limit=limit)
    return [PrimeiroSocorroResponse.model_validate(x) for x in items]


async def _salvar_imagem_ps(id_ps: int, file: UploadFile) -> str:
    """Guarda ficheiro em uploads/primeiros_socorros/{id}_{uuid}.{ext}; devolve path relativo."""
    ext = (Path(file.filename or "").suffix or ".jpg").lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = "jpg"
    size_limit = MAX_IMAGE_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Imagem demasiado grande. Máximo {MAX_IMAGE_SIZE_MB} MB.",
        )
    upload_path = settings.get_upload_path()
    ps_dir = upload_path / "primeiros_socorros"
    ps_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{id_ps}_{uuid.uuid4().hex[:8]}.{ext}"
    (ps_dir / filename).write_bytes(content)
    return f"primeiros_socorros/{filename}"


@router.post("/admin/", response_model=PrimeiroSocorroResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    titulo: str = Form(..., description="Título"),
    categoria: str = Form(..., description="Categoria (ex.: queimaduras, hemorragia)"),
    descricao: str = Form(""),
    instrucoes: str = Form(""),
    video_url: str = Form("", description="URL do vídeo (ex.: YouTube)"),
    ordem: int = Form(0),
    ativo: bool = Form(True),
    imagem: UploadFile | None = File(None, description="Imagem (ficheiro)"),
):
    """Autoridade: cadastra um novo item. Imagem enviada como ficheiro; vídeo como URL."""
    data = {
        "titulo": titulo.strip(),
        "categoria": categoria.strip(),
        "descricao": descricao.strip() or None,
        "instrucoes": instrucoes.strip() or None,
        "video_url": video_url.strip() or None,
        "ordem": ordem,
        "ativo": ativo,
        "imagem_url": None,
    }
    ps = criar_primeiro_socorro(db, data)
    if imagem and (imagem.filename or "").strip():
        url_path = await _salvar_imagem_ps(ps.id, imagem)
        atualizar_primeiro_socorro(db, ps.id, {"imagem_url": url_path})
        ps = obter_primeiro_socorro(db, ps.id)
    return PrimeiroSocorroResponse.model_validate(ps)


@router.post("/admin/{id_ps}/imagem", response_model=PrimeiroSocorroResponse)
async def upload_imagem(
    id_ps: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    imagem: UploadFile = File(..., description="Imagem (ficheiro)"),
):
    """Autoridade: envia ou substitui a imagem do item de primeiros socorros."""
    ps = obter_primeiro_socorro(db, id_ps)
    if not ps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não encontrado.")
    url_path = await _salvar_imagem_ps(id_ps, imagem)
    atualizar_primeiro_socorro(db, id_ps, {"imagem_url": url_path})
    ps = obter_primeiro_socorro(db, id_ps)
    return PrimeiroSocorroResponse.model_validate(ps)


@router.get("/admin/{id_ps}", response_model=PrimeiroSocorroResponse)
def obter_admin(
    id_ps: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    ps = obter_primeiro_socorro(db, id_ps)
    if not ps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não encontrado.")
    return PrimeiroSocorroResponse.model_validate(ps)


@router.patch("/admin/{id_ps}", response_model=PrimeiroSocorroResponse)
def atualizar(
    id_ps: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    data: PrimeiroSocorroUpdate = ...,
):
    ps = atualizar_primeiro_socorro(db, id_ps, data.model_dump(exclude_unset=True))
    if not ps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não encontrado.")
    return PrimeiroSocorroResponse.model_validate(ps)


@router.delete("/admin/{id_ps}", status_code=status.HTTP_204_NO_CONTENT)
def apagar(
    id_ps: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    if not apagar_primeiro_socorro(db, id_ps):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não encontrado.")
    return None
