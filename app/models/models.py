"""
Modelos SQLAlchemy para o SOS Angola.
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


# --- Enums ---
class TipoAutoridade(str, enum.Enum):
    POLICIA = "policia"
    BOMBEIROS = "bombeiros"
    AMBULANCIA = "ambulancia"
    PROTECCAO_CIVIL = "proteccao_civil"
    OUTRO = "outro"


class TipoAlerta(str, enum.Enum):
    SOS_RAPIDO = "sos_rapido"       # Botão ou volume - sem login
    SOS_FORMULARIO = "sos_formulario"  # Com formulário - logado
    ALERTA_FAMILIAR = "alerta_familiar"  # Para familiares/amigos
    MEDICACAO_NAO_CUMPRIDA = "medicacao_nao_cumprida"  # 3 doses ignoradas seguidas


class EstadoAlerta(str, enum.Enum):
    PENDENTE = "pendente"
    EM_ATENDIMENTO = "em_atendimento"
    RESOLVIDO = "resolvido"
    CANCELADO = "cancelado"


class TipoPaciente(str, enum.Enum):
    IDOSO = "idoso"
    PACIENTE_CRONICO = "paciente_cronico"
    POS_CIRURGIA = "pos_cirurgia"
    OUTRO = "outro"


class FrequenciaMonitorizacao(str, enum.Enum):
    DIARIA = "diaria"
    SEMANAL = "semanal"


# --- Localização ---
class Provincia(Base):
    __tablename__ = "provincia"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)
    ativo = Column(Boolean, default=True)
    municipios = relationship("Municipio", back_populates="provincia")


class Municipio(Base):
    __tablename__ = "municipio"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_provincia = Column(Integer, ForeignKey("provincia.id"), nullable=False)
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, default=True)
    provincia = relationship("Provincia", back_populates="municipios")
    autoridades = relationship("Autoridade", back_populates="municipio")


# --- Autoridades (gestão dashboard: qual autoridade mais próxima, etc.) ---
class Autoridade(Base):
    __tablename__ = "autoridade"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_municipio = Column(Integer, ForeignKey("municipio.id"), nullable=True)
    nome = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)  # TipoAutoridade
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    endereco = Column(Text, nullable=True)
    telefone = Column(String(20), nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    municipio = relationship("Municipio", back_populates="autoridades")
    usuarios = relationship("UsuarioAutoridade", back_populates="autoridade")
    alertas_atribuidos = relationship("Alerta", back_populates="autoridade_atribuida")


class UsuarioAutoridade(Base):
    """Login para o dashboard das autoridades."""
    __tablename__ = "usuario_autoridade"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_autoridade = Column(Integer, ForeignKey("autoridade.id"), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    nome = Column(String(150), nullable=True)
    ativo = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    autoridade = relationship("Autoridade", back_populates="usuarios")


# --- Cidadão (cadastro: nome, data_nascimento, telefone, bi, password; opcionais: email, fotografia, genero) ---
# Campos obrigatórios no registo; nullable=True para compatibilidade com BD já existentes (migração).
class Cidadao(Base):
    __tablename__ = "cidadao"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(150), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    telefone = Column(String(20), nullable=True, unique=True)
    bi = Column(String(50), nullable=True, unique=True)  # Bilhete de identidade
    password_hash = Column(String(255), nullable=True)
    # Opcionais
    email = Column(String(255), nullable=True)
    fotografia_url = Column(String(500), nullable=True)
    fotografia_base64 = Column(Text, nullable=True)  # foto de perfil em base64 (opcional)
    genero = Column(String(20), nullable=True)  # M, F, Outro, etc.
    precisa_cuidados_especiais = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    contatos_emergencia = relationship("ContatoEmergencia", back_populates="cidadao")
    alertas = relationship("Alerta", back_populates="cidadao")
    acompanhamentos = relationship("Acompanhamento", back_populates="cidadao")
    cuidados_especiais = relationship("CuidadosEspeciais", back_populates="cidadao", uselist=False)


class ContatoEmergencia(Base):
    """Contatos de emergência do cidadão (obrigatório pelo menos um). tipo: familiar, medico, cuidador, outro."""
    __tablename__ = "contato_emergencia"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cidadao = Column(Integer, ForeignKey("cidadao.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    telefone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    tipo = Column(String(30), nullable=True)  # familiar, medico, cuidador, outro
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cidadao = relationship("Cidadao", back_populates="contatos_emergencia")


# --- Cuidados especiais (quando cidadão precisa_cuidados_especiais = True) ---
class CuidadosEspeciais(Base):
    __tablename__ = "cuidados_especiais"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cidadao = Column(Integer, ForeignKey("cidadao.id"), nullable=False, unique=True)
    tipo_paciente = Column(String(50), nullable=True)  # TipoPaciente: idoso, paciente_cronico, pos_cirurgia, outro
    doencas_conhecidas = Column(Text, nullable=True)  # ex: diabetes, hipertensão, asma
    alergias = Column(Text, nullable=True)
    tipo_sanguineo = Column(String(10), nullable=True)  # A+, B+, O+, etc.
    id_medico_responsavel = Column(Integer, ForeignKey("contato_emergencia.id"), nullable=True)
    hospital_ou_clinica = Column(String(255), nullable=True)
    id_cuidador = Column(Integer, ForeignKey("contato_emergencia.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    cidadao = relationship("Cidadao", back_populates="cuidados_especiais")
    medico_responsavel = relationship("ContatoEmergencia", foreign_keys=[id_medico_responsavel])
    cuidador = relationship("ContatoEmergencia", foreign_keys=[id_cuidador])
    medicacoes = relationship("MedicacaoCidadao", back_populates="cuidados_especiais")


class MedicacaoCidadao(Base):
    """Medicamentos e horários para acompanhamento de saúde (dentro de cuidados especiais).
    Suporta: intervalo (de X em X horas), dias_semana (dias fixos + horário), intervalo_dias (a cada N dias).
    """
    __tablename__ = "medicacao_cidadao"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cuidados_especiais = Column(Integer, ForeignKey("cuidados_especiais.id"), nullable=False)
    nome_medicamento = Column(String(200), nullable=False)
    dosagem = Column(String(100), nullable=True)  # legado: texto livre
    horario_tomar = Column(String(100), nullable=True)  # legado: ex: "08:00, 20:00"
    frequencia_monitorizacao = Column(String(20), nullable=True)  # legado: diaria, semanal
    # Nova estrutura para notificações
    dose_valor = Column(Float, nullable=True)
    dose_unidade = Column(String(30), nullable=True)  # mg, comprimido, ml
    tipo_frequencia = Column(String(30), nullable=True)  # intervalo, dias_semana, intervalo_dias
    intervalo_horas = Column(Integer, nullable=True)  # para tipo_frequencia=intervalo (ex: 8 = de 8 em 8h)
    intervalo_dias = Column(Integer, nullable=True)  # para tipo_frequencia=intervalo_dias (ex: 2 = a cada 2 dias)
    dias_semana = Column(Text, nullable=True)  # JSON: ["segunda","quarta","sexta"]
    horario_fixo = Column(String(10), nullable=True)  # "09:00" para dias_semana ou intervalo_dias
    ultima_dose = Column(DateTime(timezone=True), nullable=True)
    proxima_dose = Column(DateTime(timezone=True), nullable=True)
    estado_atual = Column(String(20), nullable=True)  # pendente, tomado, ignorado
    historico_doses = Column(Text, nullable=True)  # JSON: [{"data_hora":"...","estado":"tomado"}, ...]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cuidados_especiais = relationship("CuidadosEspeciais", back_populates="medicacoes")


# --- Alertas ---
class Alerta(Base):
    __tablename__ = "alerta"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(50), nullable=False)  # TipoAlerta
    id_cidadao = Column(Integer, ForeignKey("cidadao.id"), nullable=True)  # null = anónimo
    sessao_anonima = Column(String(120), nullable=True)  # identificador de dispositivo/sessão para anónimos (um SOS ativo por dispositivo)
    id_autoridade_atribuida = Column(Integer, ForeignKey("autoridade.id"), nullable=True)
    estado = Column(String(30), default=EstadoAlerta.PENDENTE.value)
    # Localização no momento do alerta
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    endereco_aprox = Column(Text, nullable=True)
    # Última localização (streaming enquanto ocorrência ativa)
    ultima_latitude = Column(Float, nullable=True)
    ultima_longitude = Column(Float, nullable=True)
    ultima_localizacao_at = Column(DateTime(timezone=True), nullable=True)
    # Destino opcional: policia, bombeiros, ambulancia
    autoridade_destino = Column(String(30), nullable=True)
    # Subtipo por autoridade: roubo, incendio, mal_estar, etc.
    tipo_ocorrencia = Column(String(80), nullable=True)
    # Cancelamento (apenas nos primeiros 20s pelo user; depois só admin)
    motivo_cancelamento = Column(String(200), nullable=True)
    cancelado_at = Column(DateTime(timezone=True), nullable=True)
    # Formulário (quando tipo = sos_formulario)
    descricao = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=True)  # ex: assalto, incêndio, acidente
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolvido_at = Column(DateTime(timezone=True), nullable=True)
    cidadao = relationship("Cidadao", back_populates="alertas")
    autoridade_atribuida = relationship("Autoridade", back_populates="alertas_atribuidos")
    midias = relationship("MidiaOcorrencia", back_populates="alerta")


class AlertaFamiliar(Base):
    """Registo de alertas enviados para familiares/amigos (com localização)."""
    __tablename__ = "alerta_familiar"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cidadao = Column(Integer, ForeignKey("cidadao.id"), nullable=False)
    id_contato_emergencia = Column(Integer, ForeignKey("contato_emergencia.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    mensagem = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Mídia (fotos/vídeos ocorrências) ---
class MidiaOcorrencia(Base):
    __tablename__ = "midia_ocorrencia"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_alerta = Column(Integer, ForeignKey("alerta.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # image, video
    url_path = Column(String(500), nullable=False)  # path relativo ou URL
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    alerta = relationship("Alerta", back_populates="midias")


# --- Chat (cidadão <-> autoridades) ---
class ChatConversa(Base):
    __tablename__ = "chat_conversa"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_alerta = Column(Integer, ForeignKey("alerta.id"), nullable=True)  # pode ser genérico
    id_cidadao = Column(Integer, ForeignKey("cidadao.id"), nullable=False)
    id_autoridade_user = Column(Integer, ForeignKey("usuario_autoridade.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    mensagens = relationship("ChatMensagem", back_populates="conversa")


class ChatMensagem(Base):
    __tablename__ = "chat_mensagem"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_conversa = Column(Integer, ForeignKey("chat_conversa.id"), nullable=False)
    enviado_por = Column(String(20), nullable=False)  # 'cidadao' | 'autoridade'
    id_autor = Column(Integer, nullable=True)  # id_cidadao ou id_usuario_autoridade
    conteudo = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    conversa = relationship("ChatConversa", back_populates="mensagens")


# --- Acompanhamento (pacientes/idosos: notificações "está tudo bem?", última localização) ---
class Acompanhamento(Base):
    __tablename__ = "acompanhamento"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cidadao = Column(Integer, ForeignKey("cidadao.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cidadao = relationship("Cidadao", back_populates="acompanhamentos")
    notificacoes = relationship("NotificacaoAcompanhamento", back_populates="acompanhamento")


class NotificacaoAcompanhamento(Base):
    """Notificações 'está tudo bem?' enviadas ao cidadão; se não responder, autoridades veem localização."""
    __tablename__ = "notificacao_acompanhamento"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_acompanhamento = Column(Integer, ForeignKey("acompanhamento.id"), nullable=False)
    enviada_em = Column(DateTime(timezone=True), server_default=func.now())
    respondida_em = Column(DateTime(timezone=True), nullable=True)
    # Última localização conhecida (atualizada pelo app)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    acompanhamento = relationship("Acompanhamento", back_populates="notificacoes")


# --- Notícias (CRUD autoridades, consumido pelo app) ---
class Noticia(Base):
    __tablename__ = "noticia"
    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(300), nullable=False)
    resumo = Column(Text, nullable=True)
    conteudo = Column(Text, nullable=True)
    imagem_url = Column(String(500), nullable=True)
    categoria = Column(String(100), nullable=True)  # primeiros_socorros, dicas, etc.
    publicada = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
