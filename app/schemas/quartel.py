from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class QuartelCreate(BaseModel):
    nome: str
    tipo: str  # "policia" | "bombeiros" | "saude"
    latitude: float
    longitude: float
    ativo: bool = True


class QuartelUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
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
