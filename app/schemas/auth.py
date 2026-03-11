import re
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date

# Formato BI angolano: 9 dígitos + 2 letras + 3 dígitos (ex: 123456789LA000)
BI_ANGOLANO_REGEX = re.compile(r"^\d{9}[A-Za-z]{2}\d{3}$")


class LoginAutoridadeRequest(BaseModel):
    email: str
    password: str


class LoginCidadaoRequest(BaseModel):
    """Login sem palavra-passe: apenas telefone OU BI (dados guardados no dispositivo)."""
    telefone: Optional[str] = None
    bi: Optional[str] = None


class ContatoEmergenciaRegistro(BaseModel):
    """Pelo menos um contato de emergência obrigatório no registo."""
    nome: str
    telefone: str
    email: Optional[str] = None
    tipo: Optional[str] = None  # familiar, medico, cuidador, outro


class RegistroCidadaoRequest(BaseModel):
    # Obrigatórios
    nome: str
    data_nascimento: date  # YYYY-MM-DD
    telefone: str
    bi: str
    password: str
    contatos_emergencia: List[ContatoEmergenciaRegistro]  # pelo menos 1
    # Opcionais
    email: Optional[str] = None
    fotografia_url: Optional[str] = None
    fotografia_base64: Optional[str] = None  # foto de perfil em base64 (JPEG)
    genero: Optional[str] = None

    @field_validator("bi")
    @classmethod
    def bi_formato_angolano(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if not BI_ANGOLANO_REGEX.match(v):
            raise ValueError(
                "BI inválido. Use o modelo angolano: 9 números, 2 letras e 3 números (ex: 123456789LA000)."
            )
        return v

    @field_validator("contatos_emergencia")
    @classmethod
    def at_least_one_contato(cls, v: List[ContatoEmergenciaRegistro]) -> List[ContatoEmergenciaRegistro]:
        if not v or len(v) < 1:
            raise ValueError("É obrigatório ter pelo menos um contato de emergência.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str  # 'cidadao' | 'autoridade'
    user_id: int


class UserInfo(BaseModel):
    id: int
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    role: str
