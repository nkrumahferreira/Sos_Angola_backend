"""
Perfil do cidadão e contactos de emergência (app mobile).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.schemas.cidadao import (
    CidadaoPerfilUpdate,
    CidadaoPerfilResponse,
    ContatoEmergenciaCreate,
    ContatoEmergenciaResponse,
)
from app.dependencies.auth import get_current_user_id
from app.services.cidadao_service import (
    obter_cidadao,
    atualizar_perfil,
    adicionar_contato_emergencia,
    listar_contatos_emergencia,
    remover_contato_emergencia,
)

router = APIRouter(prefix="/cidadao", tags=["Cidadão"])


@router.get("/perfil", response_model=CidadaoPerfilResponse)
def obter_perfil(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    c = obter_cidadao(db, id_cidadao)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cidadão não encontrado.")
    contatos = listar_contatos_emergencia(db, id_cidadao)
    return CidadaoPerfilResponse(
        id=c.id,
        nome=c.nome,
        idade=c.idade,
        telefone=c.telefone,
        email=c.email,
        created_at=c.created_at,
        contatos_emergencia=[ContatoEmergenciaResponse.model_validate(co) for co in contatos],
    )


@router.patch("/perfil", response_model=CidadaoPerfilResponse)
def atualizar_perfil_endpoint(
    data: CidadaoPerfilUpdate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    c = atualizar_perfil(db, id_cidadao, nome=data.nome, idade=data.idade)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cidadão não encontrado.")
    contatos = listar_contatos_emergencia(db, id_cidadao)
    return CidadaoPerfilResponse(
        id=c.id,
        nome=c.nome,
        idade=c.idade,
        telefone=c.telefone,
        email=c.email,
        created_at=c.created_at,
        contatos_emergencia=[ContatoEmergenciaResponse.model_validate(co) for co in contatos],
    )


@router.post("/contatos-emergencia", response_model=ContatoEmergenciaResponse, status_code=status.HTTP_201_CREATED)
def adicionar_contato(
    data: ContatoEmergenciaCreate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    contato = adicionar_contato_emergencia(
        db, id_cidadao, nome=data.nome, telefone=data.telefone, email=data.email
    )
    return ContatoEmergenciaResponse.model_validate(contato)


@router.get("/contatos-emergencia", response_model=list[ContatoEmergenciaResponse])
def listar_contatos(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    contatos = listar_contatos_emergencia(db, id_cidadao)
    return [ContatoEmergenciaResponse.model_validate(c) for c in contatos]


@router.delete("/contatos-emergencia/{id_contato}")
def remover_contato(
  id_contato: int,
  db=Depends(get_db),
  id_cidadao: int = Depends(get_current_user_id),
):
    if not remover_contato_emergencia(db, id_contato, id_cidadao):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto não encontrado.")
    return {"message": "Contacto removido."}
