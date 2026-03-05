"""
Alertas: SOS rápido (público/anónimo), SOS formulário e alerta familiar (logado).
Dashboard: listar, atribuir autoridade, atualizar estado.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_db
from app.schemas.alerta import (
    SOSRapidoRequest,
    SOSFormularioRequest,
    AlertaFamiliarRequest,
    AlertaResponse,
    AlertaAtribuirAutoridade,
    AlertaEstadoUpdate,
)
from app.dependencies.auth import get_current_user_id_optional, get_current_user_id, require_autoridade
from app.services.alerta_service import (
    criar_sos_rapido,
    criar_sos_formulario,
    criar_alerta_familiar,
    listar_alertas,
    obter_alerta,
    atribuir_autoridade,
    atualizar_estado,
)
from app.services.cidadao_service import listar_contatos_emergencia
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.post("/sos-rapido", response_model=AlertaResponse)
async def sos_rapido(
    data: SOSRapidoRequest,
    db=Depends(get_db),
    id_cidadao: int | None = Depends(get_current_user_id_optional),
):
    """Público: qualquer um pode enviar SOS com localização (com ou sem login)."""
    alerta = criar_sos_rapido(
        db,
        latitude=data.latitude,
        longitude=data.longitude,
        endereco_aprox=data.endereco_aprox,
        id_cidadao=id_cidadao,
    )
    resp = AlertaResponse.model_validate(alerta)
    await ws_manager.broadcast_alertas({"evento": "novo_alerta", "alerta": resp.model_dump(mode="json")})
    return resp


@router.post("/sos-formulario", response_model=AlertaResponse)
async def sos_formulario(
    data: SOSFormularioRequest,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Cidadão logado: alerta com formulário + localização."""
    alerta = criar_sos_formulario(
        db,
        id_cidadao=id_cidadao,
        latitude=data.latitude,
        longitude=data.longitude,
        endereco_aprox=data.endereco_aprox,
        descricao=data.descricao,
        categoria=data.categoria,
    )
    resp = AlertaResponse.model_validate(alerta)
    await ws_manager.broadcast_alertas({"evento": "novo_alerta", "alerta": resp.model_dump(mode="json")})
    return resp


@router.post("/alerta-familiar", response_model=dict)
def alerta_familiar(
    data: AlertaFamiliarRequest,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Cidadão logado: envia alerta com localização para um contacto de emergência."""
    contatos = listar_contatos_emergencia(db, id_cidadao)
    if not any(c.id == data.id_contato_emergencia for c in contatos):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto de emergência não encontrado.")
    af = criar_alerta_familiar(
        db,
        id_cidadao=id_cidadao,
        id_contato_emergencia=data.id_contato_emergencia,
        latitude=data.latitude,
        longitude=data.longitude,
        mensagem=data.mensagem,
    )
    return {"id": af.id, "message": "Alerta enviado aos familiares."}


@router.get("/meus", response_model=list[AlertaResponse])
def meus_alertas(
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Cidadão logado: lista os seus alertas."""
    alertas = listar_alertas(db, id_cidadao=id_cidadao, skip=skip, limit=limit)
    return [AlertaResponse.model_validate(a) for a in alertas]


# --- Dashboard autoridades ---
@router.get("/", response_model=list[AlertaResponse])
def listar_alertas_endpoint(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    estado: str | None = Query(None),
    tipo: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    alertas = listar_alertas(db, estado=estado, tipo=tipo, skip=skip, limit=limit)
    return [AlertaResponse.model_validate(a) for a in alertas]


@router.get("/{alerta_id}", response_model=AlertaResponse)
def obter_alerta_endpoint(
    alerta_id: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    alerta = obter_alerta(db, alerta_id)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    return AlertaResponse.model_validate(alerta)


@router.patch("/{alerta_id}/atribuir", response_model=AlertaResponse)
def atribuir_autoridade_endpoint(
  alerta_id: int,
  body: AlertaAtribuirAutoridade,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    alerta = atribuir_autoridade(db, alerta_id, body.id_autoridade)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    return AlertaResponse.model_validate(alerta)


@router.patch("/{alerta_id}/estado", response_model=AlertaResponse)
def atualizar_estado_endpoint(
  alerta_id: int,
  body: AlertaEstadoUpdate,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    alerta = atualizar_estado(db, alerta_id, body.estado)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    return AlertaResponse.model_validate(alerta)
