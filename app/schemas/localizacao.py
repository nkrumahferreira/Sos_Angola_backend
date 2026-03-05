from pydantic import BaseModel
from typing import Optional, List


class ProvinciaResponse(BaseModel):
    id: int
    nome: str
    ativo: bool

    class Config:
        from_attributes = True


class MunicipioResponse(BaseModel):
    id: int
    id_provincia: int
    nome: str
    ativo: bool

    class Config:
        from_attributes = True
