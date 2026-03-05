from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ContatoEmergenciaCreate(BaseModel):
    nome: str
    telefone: str
    email: Optional[str] = None


class ContatoEmergenciaResponse(BaseModel):
    id: int
    nome: str
    telefone: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


class CidadaoPerfilUpdate(BaseModel):
    nome: Optional[str] = None
    idade: Optional[int] = None


class CidadaoPerfilResponse(BaseModel):
    id: int
    nome: Optional[str] = None
    idade: Optional[int] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    contatos_emergencia: List[ContatoEmergenciaResponse] = []

    class Config:
        from_attributes = True
