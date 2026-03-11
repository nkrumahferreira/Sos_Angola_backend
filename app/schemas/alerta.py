from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LocalizacaoInput(BaseModel):
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None


# SOS rápido (anon ou logado) - localização + opcionalmente autoridade e tipo. Anónimos: device_id obrigatório para um SOS ativo por dispositivo.
class SOSRapidoRequest(BaseModel):
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None
    autoridade_destino: Optional[str] = None  # policia, bombeiros, ambulancia
    tipo_ocorrencia: Optional[str] = None  # roubo, incendio, mal_estar, etc.
    device_id: Optional[str] = None  # obrigatório para anónimos: identificador de dispositivo/sessão (um SOS ativo por dispositivo)


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
    ultima_latitude: Optional[float] = None
    ultima_longitude: Optional[float] = None
    ultima_localizacao_at: Optional[datetime] = None
    autoridade_destino: Optional[str] = None
    tipo_ocorrencia: Optional[str] = None
    motivo_cancelamento: Optional[str] = None
    cancelado_at: Optional[datetime] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CancelarAlertaRequest(BaseModel):
    motivo: str  # toque_acidental, falso_alarme, etc.
    device_id: Optional[str] = None  # obrigatório para anónimos: identifica o dispositivo que pode cancelar


class AtualizarLocalizacaoAlertaRequest(BaseModel):
    latitude: float
    longitude: float
    device_id: Optional[str] = None  # obrigatório para anónimos


class TransformarFormularioRequest(BaseModel):
    """Converte um SOS rápido em SOS detalhado (escolha de autoridade e tipo de ocorrência)."""
    autoridade_destino: str  # policia, bombeiros, ambulancia
    tipo_ocorrencia: str    # roubo, incendio, mal_estar, etc.
    descricao: Optional[str] = None


class AlertaAtribuirAutoridade(BaseModel):
    id_autoridade: int


class AlertaEstadoUpdate(BaseModel):
    estado: str
    motivo: Optional[str] = None  # para cancelado (admin)
class MidiaOcorrenciaResponse(BaseModel):
    """Mídia associada a um alerta (ex.: vídeo do relatório da ocorrência)."""
    id: int
    id_alerta: int
    tipo: str  # image, video
    url_path: str  # path relativo; URL completo: {API_BASE}/uploads/{url_path}
    created_at: datetime

    class Config:
        from_attributes = True
