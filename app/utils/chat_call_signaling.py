"""
Signaling WebSocket para chamadas de voz e vídeo (WebRTC) no chat.
Uma conversa pode ter um cidadão e N autoridades; chamadas 1-to-1 (cidadao <-> uma autoridade).
Mensagens: call_request, call_accept, call_reject, offer, answer, ice, hangup.
"""
import asyncio
import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket


class ChatCallSignalingManager:
    """Salas por id_conversa: um cidadão e N autoridades; signaling para WebRTC (offer/answer/ice)."""

    def __init__(self):
        # id_conversa -> { "cidadao": WebSocket | None, "autoridades": set(WebSocket) }
        self._rooms: Dict[int, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _room(self, id_conversa: int) -> Dict[str, Any]:
        if id_conversa not in self._rooms:
            self._rooms[id_conversa] = {"cidadao": None, "autoridades": set()}
        return self._rooms[id_conversa]

    async def join_cidadao(self, id_conversa: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._room(id_conversa)
            if room["cidadao"] is not None:
                try:
                    await room["cidadao"].close(code=4000)
                except Exception:
                    pass
            room["cidadao"] = websocket

    async def join_autoridade(self, id_conversa: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._room(id_conversa)
            room["autoridades"].add(websocket)

    async def leave_cidadao(self, id_conversa: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(id_conversa)
            if room and room.get("cidadao") is websocket:
                room["cidadao"] = None
            self._cleanup(id_conversa)

    async def leave_autoridade(self, id_conversa: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(id_conversa)
            if room:
                room.get("autoridades", set()).discard(websocket)
            self._cleanup(id_conversa)

    def _cleanup(self, id_conversa: int) -> None:
        room = self._rooms.get(id_conversa)
        if not room:
            return
        if room.get("cidadao") is None and not room.get("autoridades"):
            self._rooms.pop(id_conversa, None)

    async def send_to_cidadao(self, id_conversa: int, message: Any) -> bool:
        room = self._rooms.get(id_conversa)
        if not room or not room.get("cidadao"):
            return False
        ws = room["cidadao"]
        text = message if isinstance(message, str) else json.dumps(message, default=str)
        try:
            await ws.send_text(text)
            return True
        except Exception:
            return False

    async def send_to_autoridades(self, id_conversa: int, message: Any) -> bool:
        room = self._rooms.get(id_conversa)
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

    async def broadcast_from_cidadao(self, id_conversa: int, message: Any) -> None:
        await self.send_to_autoridades(id_conversa, message)

    async def broadcast_from_autoridade(self, id_conversa: int, message: Any) -> None:
        await self.send_to_cidadao(id_conversa, message)


chat_call_signaling = ChatCallSignalingManager()
