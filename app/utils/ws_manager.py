"""
Gestor de conexões WebSocket: alertas em tempo real para autoridades e chat.
"""
import asyncio
import json
from typing import Dict, Set, Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # user_id -> set of WebSocket (autoridade ou cidadão identificado por token)
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, key: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            conns = self.active_connections.get(key)
            if conns is None:
                conns = set()
                self.active_connections[key] = conns
            conns.add(websocket)

    async def register_only(self, key: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self.active_connections.get(key)
            if conns is None:
                conns = set()
                self.active_connections[key] = conns
            conns.add(websocket)

    async def disconnect(self, key: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self.active_connections.get(key)
            if conns and websocket in conns:
                conns.discard(websocket)
                try:
                    await websocket.close()
                except Exception:
                    pass
                if not conns:
                    del self.active_connections[key]

    async def send_to(self, key: str, message: Any) -> bool:
        conns = self.active_connections.get(key)
        if not conns:
            return False
        text = message if isinstance(message, str) else json.dumps(message, default=str)
        for ws in list(conns):
            try:
                await ws.send_text(text)
            except Exception:
                pass
        return True

    async def broadcast_alertas(self, message: Any) -> None:
        """Envia novo alerta para todos os clientes no canal 'alertas' (dashboard)."""
        conns = self.active_connections.get("alertas")
        if not conns:
            return
        text = message if isinstance(message, str) else json.dumps(message, default=str)
        for ws in list(conns):
            try:
                await ws.send_text(text)
            except Exception:
                pass


ws_manager = ConnectionManager()
