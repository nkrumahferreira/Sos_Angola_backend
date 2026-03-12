from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatMensagemCreate(BaseModel):
    conteudo: Optional[str] = ""
    tipo_mensagem: Optional[str] = "text"  # text | image | video
    media_url: Optional[str] = None  # path devolvido pelo upload de mídia


class ChatMensagemResponse(BaseModel):
    id: int
    id_conversa: int
    enviado_por: str
    id_autor: Optional[int] = None
    conteudo: Optional[str] = None
    tipo_mensagem: Optional[str] = "text"
    media_url: Optional[str] = None
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
