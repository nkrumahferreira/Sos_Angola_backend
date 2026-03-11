"""
Signaling WebSocket para transmissão em direto (WebRTC) por alerta.
Um cidadão publica o stream (câmara + microfone); as autoridades subscrevem e veem em tempo real.
Mensagens: offer, answer, ice (ICE candidate).
"""
import asyncio
import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket


class LiveSignalingManager:
    """Salas por alerta_id: um cidadão (publisher) e N autoridades (subscribers)."""

    def __init__(self):
        # alerta_id -> { "citizen": WebSocket | None, "autoridades": set(WebSocket) }
        self._rooms: Dict[int, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _room(self, alerta_id: int) -> Dict[str, Any]:
        if alerta_id not in self._rooms:
            self._rooms[alerta_id] = {"citizen": None, "autoridades": set()}
        return self._rooms[alerta_id]

    async def join_citizen(self, alerta_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._room(alerta_id)
            if room["citizen"] is not None:
                try:
                    await room["citizen"].close(code=4000)
                except Exception:
                    pass
            room["citizen"] = websocket

    async def join_autoridade(self, alerta_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._room(alerta_id)
            room["autoridades"].add(websocket)

    async def leave_citizen(self, alerta_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(alerta_id)
            if room and room.get("citizen") is websocket:
                room["citizen"] = None
            self._cleanup_room(alerta_id)

    async def leave_autoridade(self, alerta_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(alerta_id)
            if room:
                room.get("autoridades", set()).discard(websocket)
            self._cleanup_room(alerta_id)

    def _cleanup_room(self, alerta_id: int) -> None:
        room = self._rooms.get(alerta_id)
        if not room:
            return
        if room.get("citizen") is None and not room.get("autoridades"):
            self._rooms.pop(alerta_id, None)

    async def send_to_citizen(self, alerta_id: int, message: Any) -> bool:
        room = self._rooms.get(alerta_id)
        if not room or not room.get("citizen"):
            return False
        ws = room["citizen"]
        text = message if isinstance(message, str) else json.dumps(message, default=str)
        try:
            await ws.send_text(text)
            return True
        except Exception:
            return False

    async def send_to_autoridades(self, alerta_id: int, message: Any) -> bool:
        room = self._rooms.get(alerta_id)
        if not room or not room.get("autoridades"):
            return False
        text = message if isinstance(message, str) else json.dumps(message, default=str)
        ok = False
        for ws in list(room["autoridades"]):
            try:
                await ws.send_text(text)
                ok = True
            except Exception:
                pass
        return ok

    async def broadcast_from_citizen(self, alerta_id: int, message: Any) -> None:
        """Cidadão enviou offer ou ice → reencaminhar para todas as autoridades."""
        await self.send_to_autoridades(alerta_id, message)

    async def broadcast_from_autoridade(self, alerta_id: int, message: Any) -> None:
        """Autoridade enviou answer ou ice → reencaminhar para o cidadão."""
        await self.send_to_citizen(alerta_id, message)


live_signaling = LiveSignalingManager()
