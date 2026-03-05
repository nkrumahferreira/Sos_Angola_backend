from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AutoridadeCreate(BaseModel):
    id_municipio: Optional[int] = None
    nome: str
    tipo: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None


class AutoridadeUpdate(BaseModel):
    id_municipio: Optional[int] = None
    nome: Optional[str] = None
    tipo: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None


class AutoridadeResponse(BaseModel):
    id: int
    id_municipio: Optional[int] = None
    nome: str
    tipo: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    ativo: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AutoridadeProximaQuery(BaseModel):
    latitude: float
    longitude: float
    tipo: Optional[str] = None  # filtrar por tipo
    limite: int = 10
