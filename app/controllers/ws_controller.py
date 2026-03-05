"""
WebSocket: canal de alertas em tempo real para o dashboard das autoridades.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.ws_manager import ws_manager
from app.utils.jwt_utils import decode_access_token

ws_router = APIRouter()


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
