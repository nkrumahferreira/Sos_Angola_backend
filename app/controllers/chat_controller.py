"""
Chat entre cidadão e autoridades (por conversa/conflito).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_db
from app.schemas.chat import ChatMensagemCreate, ChatMensagemResponse, ChatConversaResponse
from app.dependencies.auth import get_current_user_id, require_autoridade
from app.services.chat_service import (
    obter_ou_criar_conversa,
    enviar_mensagem,
    listar_mensagens,
    listar_conversas_cidadao,
)
from app.models.models import ChatConversa

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/conversas", response_model=list[ChatConversaResponse])
def listar_conversas(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    """Cidadão: lista as suas conversas."""
    convs = listar_conversas_cidadao(db, id_cidadao)
    result = []
    for c in convs:
        msgs = listar_mensagens(db, c.id, skip=0, limit=500)
        result.append(ChatConversaResponse(
            id=c.id,
            id_alerta=c.id_alerta,
            id_cidadao=c.id_cidadao,
            id_autoridade_user=c.id_autoridade_user,
            created_at=c.created_at,
            mensagens=[ChatMensagemResponse.model_validate(m) for m in msgs],
        ))
    return result


@router.post("/conversas", response_model=ChatConversaResponse)
def criar_conversa(
    id_alerta: int | None = None,
  db=Depends(get_db),
  id_cidadao: int = Depends(get_current_user_id),
):
    """Cidadão: inicia conversa (opcionalmente ligada a um alerta)."""
    conv = obter_ou_criar_conversa(db, id_cidadao=id_cidadao, id_alerta=id_alerta)
    msgs = listar_mensagens(db, conv.id, skip=0, limit=500)
    return ChatConversaResponse(
        id=conv.id,
        id_alerta=conv.id_alerta,
        id_cidadao=conv.id_cidadao,
        id_autoridade_user=conv.id_autoridade_user,
        created_at=conv.created_at,
        mensagens=[ChatMensagemResponse.model_validate(m) for m in msgs],
    )


@router.get("/conversas/{id_conversa}/mensagens", response_model=list[ChatMensagemResponse])
def listar_mensagens_endpoint(
  id_conversa: int,
  db=Depends(get_db),
  id_cidadao: int = Depends(get_current_user_id),
  skip: int = Query(0, ge=0),
  limit: int = Query(100, ge=1, le=500),
):
    conv = db.query(ChatConversa).filter(
        ChatConversa.id == id_conversa,
        ChatConversa.id_cidadao == id_cidadao,
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    msgs = listar_mensagens(db, id_conversa, skip=skip, limit=limit)
    return [ChatMensagemResponse.model_validate(m) for m in msgs]


@router.post("/conversas/{id_conversa}/mensagens", response_model=ChatMensagemResponse)
def enviar_mensagem_cidadao(
  id_conversa: int,
  data: ChatMensagemCreate,
  db=Depends(get_db),
  id_cidadao: int = Depends(get_current_user_id),
):
    conv = db.query(ChatConversa).filter(
        ChatConversa.id == id_conversa,
        ChatConversa.id_cidadao == id_cidadao,
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    msg = enviar_mensagem(db, id_conversa, "cidadao", id_cidadao, data.conteudo)
    return ChatMensagemResponse.model_validate(msg)


# --- Dashboard: autoridade envia mensagem e lista conversas ---
@router.post("/admin/conversas/{id_conversa}/mensagens", response_model=ChatMensagemResponse)
def enviar_mensagem_autoridade(
  id_conversa: int,
  data: ChatMensagemCreate,
  db=Depends(get_db),
  payload=Depends(require_autoridade),
):
    """Autoridade envia mensagem na conversa. payload contém 'sub' (user_id)."""
    id_autoridade_user = int(payload.get("sub"))
    conv = db.query(ChatConversa).filter(ChatConversa.id == id_conversa).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    msg = enviar_mensagem(db, id_conversa, "autoridade", id_autoridade_user, data.conteudo)
    return ChatMensagemResponse.model_validate(msg)
