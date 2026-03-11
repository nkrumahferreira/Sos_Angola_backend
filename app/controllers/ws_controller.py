"""
WebSocket: canal de alertas em tempo real para o dashboard das autoridades;
signaling para transmissão em direto (WebRTC) por alerta.
"""
import json
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.database import get_session_local
from app.utils.ws_manager import ws_manager
from app.utils.jwt_utils import decode_access_token
from app.utils.live_signaling import live_signaling
from app.services.alerta_service import obter_alerta

ws_router = APIRouter()

ESTADOS_ATIVOS_LIVE = ("pendente", "em_atendimento")

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@ws_router.get("/live-viewer", response_class=FileResponse)
def live_viewer_page():
    """Página para a autoridade ver em direto o stream do cidadão (WebRTC). Use ?alerta_id=1&token=JWT."""
    path = _STATIC_DIR / "live-viewer.html"
    if not path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Página não encontrada.")
    return FileResponse(path)


@ws_router.websocket("/ws/alertas")
async def websocket_alertas(websocket: WebSocket):
    """
    Canal para o dashboard receber novos alertas em tempo real.
    Token opcional: se enviado (query ?token=xxx), valida que é autoridade.
    """
    await websocket.accept()
    token = websocket.query_params.get("token")
    if token:
        if token.startswith("Bearer "):
            token = token[7:].strip()
        payload = decode_access_token(token)
        if payload and payload.get("role") != "autoridade":
            await websocket.close(code=4001)
            return
    try:
        await ws_manager.register_only("alertas", websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await ws_manager.disconnect("alertas", websocket)
        except Exception:
            pass


@ws_router.websocket("/ws/live/{alerta_id}")
async def websocket_live_signaling(websocket: WebSocket, alerta_id: int):
    """
    Signaling WebRTC para transmissão em direto do cidadão para as autoridades.
    Query: role=citizen&token=xxx OU role=citizen&device_id=xxx (anónimos) | role=autoridade&token=xxx
    Mensagens JSON: { "type": "offer"|"answer"|"ice", "payload": ... }
    """
    await websocket.accept()
    role = (websocket.query_params.get("role") or "").strip().lower()
    token = websocket.query_params.get("token")
    if token and token.startswith("Bearer "):
        token = token[7:].strip()
    device_id = (websocket.query_params.get("device_id") or "").strip() or None

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        alerta = obter_alerta(db, alerta_id)
        if not alerta:
            await websocket.close(code=4404)
            return
        if alerta.estado not in ESTADOS_ATIVOS_LIVE:
            await websocket.close(code=4403)
            return

        if role == "citizen":
            # Cidadão: dono do alerta (id_cidadao ou sessao_anonima)
            ok = False
            if token:
                payload = decode_access_token(token)
                if payload and payload.get("sub") and str(alerta.id_cidadao) == str(payload.get("sub")):
                    ok = True
            if not ok and device_id and alerta.sessao_anonima == device_id:
                ok = True
            if not ok:
                await websocket.close(code=4403)
                return
            await live_signaling.join_citizen(alerta_id, websocket)
        elif role == "autoridade":
            if not token:
                await websocket.close(code=4401)
                return
            payload = decode_access_token(token)
            if not payload or payload.get("role") != "autoridade":
                await websocket.close(code=4401)
                return
            await live_signaling.join_autoridade(alerta_id, websocket)
        else:
            await websocket.close(code=4400)
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
            payload = msg.get("payload")
            camera = msg.get("camera")
            if t == "offer" or t == "answer":
                out = {"type": t, "payload": payload}
                if camera is not None:
                    out["camera"] = camera
                if role == "citizen":
                    await live_signaling.broadcast_from_citizen(alerta_id, out)
                else:
                    await live_signaling.broadcast_from_autoridade(alerta_id, out)
            elif t == "ice":
                out = {"type": "ice", "payload": payload}
                if camera is not None:
                    out["camera"] = camera
                if role == "citizen":
                    await live_signaling.broadcast_from_citizen(alerta_id, out)
                else:
                    await live_signaling.broadcast_from_autoridade(alerta_id, out)
            elif t == "switch_camera":
                if role == "autoridade":
                    await live_signaling.send_to_citizen(alerta_id, {"type": "switch_camera", "payload": payload})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if role == "citizen":
            await live_signaling.leave_citizen(alerta_id, websocket)
        else:
            await live_signaling.leave_autoridade(alerta_id, websocket)
