from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatMensagemCreate(BaseModel):
    conteudo: str


class ChatMensagemResponse(BaseModel):
    id: int
    id_conversa: int
    enviado_por: str
    id_autor: Optional[int] = None
    conteudo: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatConversaResponse(BaseModel):
    id: int
    id_alerta: Optional[int] = None
    id_cidadao: int
    id_autoridade_user: Optional[int] = None
    created_at: datetime
    mensagens: list[ChatMensagemResponse] = []

    class Config:
        from_attributes = True
