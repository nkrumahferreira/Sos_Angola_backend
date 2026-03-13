from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

TipoQuartelLiteral = Literal["policia", "bombeiros", "saude"]


class QuartelCreate(BaseModel):
    nome: str
    tipo: TipoQuartelLiteral
    latitude: float
    longitude: float
    ativo: bool = True


class QuartelUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[TipoQuartelLiteral] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ativo: Optional[bool] = None


class QuartelResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    latitude: float
    longitude: float
    ativo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
