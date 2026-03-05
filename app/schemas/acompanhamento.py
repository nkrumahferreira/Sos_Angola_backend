from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AcompanhamentoCreate(BaseModel):
    id_cidadao: int


class AcompanhamentoResponse(BaseModel):
    id: int
    id_cidadao: int
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificacaoAcompanhamentoResponse(BaseModel):
    id: int
    id_acompanhamento: int
    enviada_em: datetime
    respondida_em: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True
