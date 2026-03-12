"""
Chat entre cidadão e autoridades (por conversa/conflito). Mensagens de texto, imagem e vídeo.
WebSocket para mensagens em tempo real.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, WebSocket, WebSocketDisconnect

from app.config import settings
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
from app.utils.ws_manager import ws_manager
from app.utils.jwt_utils import decode_access_token
from app.utils.chat_call_signaling import chat_call_signaling

router = APIRouter(prefix="/chat", tags=["Chat"])

def _chat_room_key(id_conversa: int) -> str:
    return f"chat_conv_{id_conversa}"

ALLOWED_CHAT_MEDIA = {"jpg", "jpeg", "png", "gif", "webp", "mp4", "webm", "mov"}
MAX_CHAT_MEDIA_MB = 50


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


@router.websocket("/conversas/{id_conversa}/ws")
async def websocket_chat_conversa(websocket: WebSocket, id_conversa: int):
    """
    WebSocket para receber mensagens em tempo real na conversa.
    Query: token=Bearer_xxx (cidadão ou autoridade com acesso à conversa).
    O servidor envia { "evento": "nova_mensagem", "mensagem": ChatMensagemResponse } quando há nova mensagem.
    """
    token = (websocket.query_params.get("token") or "").strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    if not token:
        await websocket.close(code=4401)
        return
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4401)
        return
    role = payload.get("role")
    sub = payload.get("sub")
    try:
        sub_id = int(sub) if sub is not None else None
    except (ValueError, TypeError):
        sub_id = None
    if not sub_id:
        await websocket.close(code=4401)
        return
    from app.database import get_session_local
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        conv = db.query(ChatConversa).filter(ChatConversa.id == id_conversa).first()
        if not conv:
            await websocket.close(code=4404)
            return
        if role == "autoridade":
            pass
        elif role != "cidadao" or conv.id_cidadao != sub_id:
            await websocket.close(code=4403)
            return
    finally:
        db.close()
    await ws_manager.connect(_chat_room_key(id_conversa), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(_chat_room_key(id_conversa), websocket)


@router.websocket("/ws/call/{id_conversa}")
async def websocket_chat_call(websocket: WebSocket, id_conversa: int):
    """
    Signaling WebRTC para chamadas de voz/vídeo na conversa.
    Query: token=xxx&role=cidadao|autoridade.
    Mensagens JSON: type=call_request|call_accept|call_reject|offer|answer|ice|hangup, payload=...
    """
    import json
    token = (websocket.query_params.get("token") or "").strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    if not token:
        await websocket.close(code=4401)
        return
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4401)
        return
    role = (payload.get("role") or "").strip().lower()
    sub = payload.get("sub")
    try:
        sub_id = int(sub) if sub is not None else None
    except (ValueError, TypeError):
        sub_id = None
    if not sub_id:
        await websocket.close(code=4401)
        return
    from app.database import get_session_local
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        conv = db.query(ChatConversa).filter(ChatConversa.id == id_conversa).first()
        if not conv:
            await websocket.close(code=4404)
            return
        if role == "autoridade":
            await chat_call_signaling.join_autoridade(id_conversa, websocket)
        elif role == "cidadao" and conv.id_cidadao == sub_id:
            await chat_call_signaling.join_cidadao(id_conversa, websocket)
        else:
            await websocket.close(code=4403)
            return
    finally:
        db.close()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            t = (msg.get("type") or "").strip().lower()
            out = {"type": t, "payload": msg.get("payload")}
            if role == "cidadao":
                await chat_call_signaling.broadcast_from_cidadao(id_conversa, out)
            else:
                await chat_call_signaling.broadcast_from_autoridade(id_conversa, out)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if role == "cidadao":
            await chat_call_signaling.leave_cidadao(id_conversa, websocket)
        else:
            await chat_call_signaling.leave_autoridade(id_conversa, websocket)


@router.post("/conversas/{id_conversa}/mensagens", response_model=ChatMensagemResponse)
async def enviar_mensagem_cidadao(
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
    msg = enviar_mensagem(
        db, id_conversa, "cidadao", id_cidadao,
        conteudo=data.conteudo or "",
        tipo_mensagem=data.tipo_mensagem or "text",
        media_url=data.media_url,
    )
    resp = ChatMensagemResponse.model_validate(msg)
    await ws_manager.send_to(_chat_room_key(id_conversa), {"evento": "nova_mensagem", "mensagem": resp.model_dump(mode="json")})
    return resp


async def _salvar_midia_chat(id_conversa: int, file: UploadFile, tipo: str) -> str:
    ext = (Path(file.filename or "").suffix or ".jpg").lower().lstrip(".")
    if ext not in ALLOWED_CHAT_MEDIA:
        ext = "jpg"
    size_limit = MAX_CHAT_MEDIA_MB * 1024 * 1024
    content = await file.read()
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ficheiro demasiado grande. Máximo {MAX_CHAT_MEDIA_MB} MB.",
        )
    upload_path = settings.get_upload_path()
    chat_dir = upload_path / "chat" / str(id_conversa)
    chat_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    (chat_dir / filename).write_bytes(content)
    return f"chat/{id_conversa}/{filename}"


@router.post("/conversas/{id_conversa}/midia")
async def upload_midia_chat(
    id_conversa: int,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
    ficheiro: UploadFile = File(..., description="Foto ou vídeo"),
):
    """Cidadão: envia foto ou vídeo para a conversa. Devolve url_path para usar em POST mensagens com media_url e tipo_mensagem (image|video)."""
    conv = db.query(ChatConversa).filter(
        ChatConversa.id == id_conversa,
        ChatConversa.id_cidadao == id_cidadao,
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    ext = (Path(ficheiro.filename or "").suffix or "").lower().lstrip(".")
    tipo = "video" if ext in ("mp4", "webm", "mov") else "image"
    url_path = await _salvar_midia_chat(id_conversa, ficheiro, tipo)
    return {"url_path": url_path, "tipo_mensagem": tipo}


# --- Dashboard: autoridade envia mensagem e lista conversas ---
@router.post("/admin/conversas/{id_conversa}/mensagens", response_model=ChatMensagemResponse)
async def enviar_mensagem_autoridade(
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
    msg = enviar_mensagem(
        db, id_conversa, "autoridade", id_autoridade_user,
        conteudo=data.conteudo or "",
        tipo_mensagem=data.tipo_mensagem or "text",
        media_url=data.media_url,
    )
    resp = ChatMensagemResponse.model_validate(msg)
    await ws_manager.send_to(_chat_room_key(id_conversa), {"evento": "nova_mensagem", "mensagem": resp.model_dump(mode="json")})
    return resp
