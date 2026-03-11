import json
from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime, date


# --- Contatos de emergência ---
class ContatoEmergenciaCreate(BaseModel):
    nome: str
    telefone: str
    email: Optional[str] = None
    tipo: Optional[str] = None  # familiar, medico, cuidador, outro


class ContatoEmergenciaUpdate(BaseModel):
    tipo: Optional[str] = None  # familiar, medico, cuidador, enfermeiro, outro


class ContatoEmergenciaResponse(BaseModel):
    id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    tipo: Optional[str] = None

    class Config:
        from_attributes = True


# --- Perfil cidadão ---
class CidadaoPerfilUpdate(BaseModel):
    nome: Optional[str] = None
    data_nascimento: Optional[date] = None
    email: Optional[str] = None
    fotografia_url: Optional[str] = None
    fotografia_base64: Optional[str] = None  # foto de perfil em base64 (JPEG)
    genero: Optional[str] = None
    precisa_cuidados_especiais: Optional[bool] = None


class CidadaoPerfilResponse(BaseModel):
    id: int
    nome: Optional[str] = None
    data_nascimento: Optional[date] = None
    telefone: Optional[str] = None
    bi: Optional[str] = None
    email: Optional[str] = None
    fotografia_url: Optional[str] = None
    genero: Optional[str] = None
    precisa_cuidados_especiais: bool = False
    created_at: Optional[datetime] = None
    contatos_emergencia: List[ContatoEmergenciaResponse] = []

    class Config:
        from_attributes = True


# --- Cuidados especiais ---
class DoseSchema(BaseModel):
    valor: float
    unidade: str  # mg, comprimido, ml


class FrequenciaIntervaloSchema(BaseModel):
    tipo: str = "intervalo"
    intervalo_horas: int


class FrequenciaDiasSemanaSchema(BaseModel):
    tipo: str = "dias_semana"
    dias: List[str]  # ["segunda", "quarta", "sexta"]
    horario: str  # "09:00"


class FrequenciaIntervaloDiasSchema(BaseModel):
    tipo: str = "intervalo_dias"
    intervalo_dias: int  # a cada N dias
    horario: str  # "09:00"


class MedicacaoCreate(BaseModel):
    nome_medicamento: str
    dosagem: Optional[str] = None
    horario_tomar: Optional[str] = None
    frequencia_monitorizacao: Optional[str] = None
    # Nova estrutura
    dose_valor: Optional[float] = None
    dose_unidade: Optional[str] = None
    tipo_frequencia: Optional[str] = None  # intervalo, dias_semana, intervalo_dias
    intervalo_horas: Optional[int] = None
    intervalo_dias: Optional[int] = None
    dias_semana: Optional[List[str]] = None
    horario_fixo: Optional[str] = None  # HH:MM


class MedicacaoResponse(BaseModel):
    id: int
    nome_medicamento: str
    dosagem: Optional[str] = None
    horario_tomar: Optional[str] = None
    frequencia_monitorizacao: Optional[str] = None
    dose_valor: Optional[float] = None
    dose_unidade: Optional[str] = None
    tipo_frequencia: Optional[str] = None
    intervalo_horas: Optional[int] = None
    intervalo_dias: Optional[int] = None
    dias_semana: Optional[List[str]] = None
    horario_fixo: Optional[str] = None
    ultima_dose: Optional[datetime] = None
    proxima_dose: Optional[datetime] = None
    estado_atual: Optional[str] = None
    historico_doses: Optional[List[dict]] = None

    @field_validator("dias_semana", mode="before")
    @classmethod
    def parse_dias_semana(cls, v: Any) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @field_validator("historico_doses", mode="before")
    @classmethod
    def parse_historico_doses(cls, v: Any) -> Optional[List[dict]]:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    class Config:
        from_attributes = True


class RegistarDoseIgnoradaRequest(BaseModel):
    """Body para registar que o cidadão não tomou a dose (para alerta às autoridades se 3 seguidas)."""
    latitude: float
    longitude: float
    endereco_aprox: Optional[str] = None


class CuidadosEspeciaisCreate(BaseModel):
    tipo_paciente: Optional[str] = None  # idoso, paciente_cronico, pos_cirurgia, outro
    doencas_conhecidas: Optional[str] = None
    alergias: Optional[str] = None
    tipo_sanguineo: Optional[str] = None
    id_medico_responsavel: Optional[int] = None  # FK contato_emergencia
    hospital_ou_clinica: Optional[str] = None
    id_cuidador: Optional[int] = None  # FK contato_emergencia
    medicacoes: Optional[List[MedicacaoCreate]] = None


class CuidadosEspeciaisUpdate(BaseModel):
    tipo_paciente: Optional[str] = None
    doencas_conhecidas: Optional[str] = None
    alergias: Optional[str] = None
    tipo_sanguineo: Optional[str] = None
    id_medico_responsavel: Optional[int] = None
    hospital_ou_clinica: Optional[str] = None
    id_cuidador: Optional[int] = None


class CuidadosEspeciaisResponse(BaseModel):
    id: int
    id_cidadao: int
    tipo_paciente: Optional[str] = None
    doencas_conhecidas: Optional[str] = None
    alergias: Optional[str] = None
    tipo_sanguineo: Optional[str] = None
    id_medico_responsavel: Optional[int] = None
    hospital_ou_clinica: Optional[str] = None
    id_cuidador: Optional[int] = None
    medicacoes: List[MedicacaoResponse] = []

    class Config:
        from_attributes = True
