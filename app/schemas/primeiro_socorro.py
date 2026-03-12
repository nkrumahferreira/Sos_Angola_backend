from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PrimeiroSocorroCreate(BaseModel):
    """Campos para criar item. A imagem é enviada como ficheiro (upload), não como URL."""
    titulo: str
    categoria: str  # queimaduras, hemorragia, paragem_cardiaca, engasgamento, fraturas, etc.
    descricao: Optional[str] = None
    instrucoes: Optional[str] = None
    # imagem: enviar via endpoint multipart (file); guardado em imagem_url no modelo
    video_url: Optional[str] = None  # URL externa (ex.: YouTube)
    ordem: int = 0
    ativo: bool = True


class PrimeiroSocorroUpdate(BaseModel):
    titulo: Optional[str] = None
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    instrucoes: Optional[str] = None
    imagem_url: Optional[str] = None
    video_url: Optional[str] = None
    ordem: Optional[int] = None
    ativo: Optional[bool] = None


class PrimeiroSocorroResponse(BaseModel):
    id: int
    titulo: str
    categoria: str
    descricao: Optional[str] = None
    instrucoes: Optional[str] = None
    imagem_url: Optional[str] = None
    video_url: Optional[str] = None
    ordem: int
    ativo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
