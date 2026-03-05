from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NoticiaCreate(BaseModel):
    titulo: str
    resumo: Optional[str] = None
    conteudo: Optional[str] = None
    imagem_url: Optional[str] = None
    categoria: Optional[str] = None
    publicada: bool = False


class NoticiaUpdate(BaseModel):
    titulo: Optional[str] = None
    resumo: Optional[str] = None
    conteudo: Optional[str] = None
    imagem_url: Optional[str] = None
    categoria: Optional[str] = None
    publicada: Optional[bool] = None


class NoticiaResponse(BaseModel):
    id: int
    titulo: str
    resumo: Optional[str] = None
    conteudo: Optional[str] = None
    imagem_url: Optional[str] = None
    categoria: Optional[str] = None
    publicada: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
