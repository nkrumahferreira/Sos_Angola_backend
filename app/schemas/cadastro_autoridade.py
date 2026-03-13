"""
Schemas para Cadastro de Autoridades (nome, tipo, quartel, telefone, email, senha).
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class CadastroAutoridadeCreate(BaseModel):
    nome: str
    tipo: str  # "admin" | "policial" | "bombeiro" | "medico"
    id_quartel: int
    telefone: Optional[str] = None
    email: EmailStr
    senha: str
    ativo: bool = True


class CadastroAutoridadeUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    id_quartel: Optional[int] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    ativo: Optional[bool] = None


class CadastroAutoridadeResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    id_quartel: int
    nome_quartel: Optional[str] = None
    tipo_quartel: Optional[str] = None
    telefone: Optional[str] = None
    email: str
    ativo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
