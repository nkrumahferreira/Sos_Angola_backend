from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LocalizacaoInput(BaseModel):
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None


# SOS rápido (anon ou logado) - só localização
class SOSRapidoRequest(BaseModel):
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None


# SOS com formulário (logado)
class SOSFormularioRequest(BaseModel):
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None


# Alerta para familiares
class AlertaFamiliarRequest(BaseModel):
    id_contato_emergencia: int
    latitude: float
    longitude: float
    mensagem: Optional[str] = None


class AlertaResponse(BaseModel):
    id: int
    tipo: str
    id_cidadao: Optional[int] = None
    id_autoridade_atribuida: Optional[int] = None
    estado: str
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertaAtribuirAutoridade(BaseModel):
    id_autoridade: int


class AlertaEstadoUpdate(BaseModel):
    estado: str
