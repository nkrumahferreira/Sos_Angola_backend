"""
Cadastro de Autoridades: CRUD para pessoas vinculadas a um quartel (nome, tipo, quartel, telefone, email, senha).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_db
from app.schemas.cadastro_autoridade import (
    CadastroAutoridadeCreate,
    CadastroAutoridadeUpdate,
    CadastroAutoridadeResponse,
)
from app.dependencies.auth import require_autoridade
from app.services.cadastro_autoridade_service import (
    listar_cadastros,
    obter_cadastro,
    obter_por_email,
    criar_cadastro,
    atualizar_cadastro,
    apagar_cadastro,
)
from app.services.quartel_service import obter_quartel

router = APIRouter(prefix="/cadastro-autoridades", tags=["Cadastro de Autoridades"])

TIPOS_VALIDOS = {"admin", "policial", "bombeiro", "medico"}


def _validar_tipo(tipo: str | None) -> None:
    if tipo and tipo.lower() not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo inválido. Use: {', '.join(sorted(TIPOS_VALIDOS))}",
        )


# Tipo da autoridade -> tipo de quartel permitido (None = qualquer)
AUTORIDADE_QUARTEL_TIPO = {
    "admin": None,
    "policial": "policia",
    "bombeiro": "bombeiros",
    "medico": "saude",
}


def _validar_tipo_quartel_compativel(tipo_autoridade: str, tipo_quartel: str) -> None:
    permitido = AUTORIDADE_QUARTEL_TIPO.get((tipo_autoridade or "").lower())
    if permitido is None:
        return
    if (tipo_quartel or "").lower() != permitido:
        msg = (
            f"O tipo de autoridade '{tipo_autoridade}' só pode ser atribuído a um quartel do tipo "
            f"'{permitido}'. O quartel selecionado é do tipo '{tipo_quartel}'."
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


def _response_from(row):
    return CadastroAutoridadeResponse(
        id=row.id,
        nome=row.nome,
        tipo=row.tipo,
        id_quartel=row.id_quartel,
        nome_quartel=row.quartel.nome if row.quartel else None,
        tipo_quartel=row.quartel.tipo if row.quartel else None,
        telefone=row.telefone,
        email=row.email,
        ativo=row.ativo,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/", response_model=list[CadastroAutoridadeResponse])
def listar(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    tipo: str | None = Query(None, description="Filtrar por tipo: admin, policial, bombeiro, medico"),
    id_quartel: int | None = Query(None, description="Filtrar por quartel"),
    ativo: bool | None = Query(None),
    nome: str | None = Query(None, description="Pesquisar por nome (parcial)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    if tipo:
        _validar_tipo(tipo)
    items = listar_cadastros(
        db, tipo=tipo, id_quartel=id_quartel, ativo=ativo, nome=nome, skip=skip, limit=limit
    )
    return [_response_from(i) for i in items]


@router.post("/", response_model=CadastroAutoridadeResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: CadastroAutoridadeCreate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    _validar_tipo(data.tipo)
    quartel = obter_quartel(db, data.id_quartel)
    if not quartel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quartel não encontrado.",
        )
    _validar_tipo_quartel_compativel(data.tipo, quartel.tipo)
    email_norm = data.email.strip().lower()
    if obter_por_email(db, email_norm):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um cadastro com este email.",
        )
    cadastro = criar_cadastro(db, data.model_dump())
    row = obter_cadastro(db, cadastro.id)
    return _response_from(row)


@router.get("/{id_cadastro}", response_model=CadastroAutoridadeResponse)
def obter(
    id_cadastro: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    row = obter_cadastro(db, id_cadastro)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro não encontrado.")
    return _response_from(row)


@router.patch("/{id_cadastro}", response_model=CadastroAutoridadeResponse)
def atualizar(
    id_cadastro: int,
    data: CadastroAutoridadeUpdate,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    if data.tipo is not None:
        _validar_tipo(data.tipo)
    row_existente = obter_cadastro(db, id_cadastro)
    if not row_existente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro não encontrado.")
    if data.id_quartel is not None:
        quartel = obter_quartel(db, data.id_quartel)
        if not quartel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quartel não encontrado.")
        tipo_eff = data.tipo if data.tipo is not None else row_existente.tipo
        _validar_tipo_quartel_compativel(tipo_eff, quartel.tipo)
    elif data.tipo is not None and row_existente.quartel:
        _validar_tipo_quartel_compativel(data.tipo, row_existente.quartel.tipo)
    payload = data.model_dump(exclude_unset=True)
    if data.email is not None:
        email_norm = data.email.strip().lower()
        existente = obter_por_email(db, email_norm)
        if existente and existente.id != id_cadastro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cadastro com este email.",
            )
    row = atualizar_cadastro(db, id_cadastro, payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro não encontrado.")
    return _response_from(obter_cadastro(db, row.id))


@router.delete("/{id_cadastro}")
def apagar(
    id_cadastro: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    if not apagar_cadastro(db, id_cadastro):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro não encontrado.")
    return {"message": "Cadastro removido."}
