from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import Alerta, AlertaFamiliar, Cidadao, ContatoEmergencia, EstadoAlerta, TipoAlerta, MidiaOcorrencia

# Janela em segundos para o utilizador cancelar o SOS (após isso só admin pode cancelar)
JANELA_CANCELAMENTO_SEGUNDOS = 20


def _estados_ativos():
    return [EstadoAlerta.PENDENTE.value, EstadoAlerta.EM_ATENDIMENTO.value]


def obter_alerta_ativo_cidadao(db: Session, id_cidadao: int | None) -> Alerta | None:
    """Retorna o alerta ativo (pendente ou em_atendimento) do cidadão, ou None."""
    if id_cidadao is None:
        return None
    return (
        db.query(Alerta)
        .filter(
            Alerta.id_cidadao == id_cidadao,
            Alerta.estado.in_(_estados_ativos()),
        )
        .order_by(Alerta.created_at.desc())
        .first()
    )


def obter_alerta_ativo_por_dispositivo(db: Session, device_id: str | None) -> Alerta | None:
    """Retorna o alerta ativo (pendente ou em_atendimento) associado ao device_id (anónimos)."""
    if not device_id or not str(device_id).strip():
        return None
    return (
        db.query(Alerta)
        .filter(
            Alerta.sessao_anonima == device_id.strip(),
            Alerta.estado.in_(_estados_ativos()),
        )
        .order_by(Alerta.created_at.desc())
        .first()
    )


def criar_sos_rapido(
    db: Session,
    latitude: float,
    longitude: float,
    endereco_aprox: str | None = None,
    id_cidadao: int | None = None,
    device_id: str | None = None,
    autoridade_destino: str | None = None,  # policia, bombeiros, ambulancia
    tipo_ocorrencia: str | None = None,
) -> Alerta:
    if id_cidadao is not None:
        alerta_ativo = obter_alerta_ativo_cidadao(db, id_cidadao)
    else:
        # Anónimo: exige device_id para limitar um SOS ativo por dispositivo
        if not device_id or not str(device_id).strip():
            raise ValueError(
                "Para utilizadores anónimos é necessário enviar um identificador de dispositivo (device_id) para limitar um SOS ativo por dispositivo."
            )
        alerta_ativo = obter_alerta_ativo_por_dispositivo(db, device_id)
    if alerta_ativo:
        raise ValueError(
            "Já tem uma ocorrência ativa. Só pode enviar outro SOS quando esta for cancelada ou concluída."
        )
    sessao_anonima = (device_id.strip() if device_id and id_cidadao is None else None)
    alerta = Alerta(
        tipo=TipoAlerta.SOS_RAPIDO.value,
        id_cidadao=id_cidadao,
        sessao_anonima=sessao_anonima,
        latitude=latitude,
        longitude=longitude,
        endereco_aprox=endereco_aprox,
        ultima_latitude=latitude,
        ultima_longitude=longitude,
        ultima_localizacao_at=datetime.now(timezone.utc),
        autoridade_destino=autoridade_destino,
        tipo_ocorrencia=tipo_ocorrencia,
        estado=EstadoAlerta.PENDENTE.value,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


def criar_sos_formulario(
    db: Session,
    id_cidadao: int,
    latitude: float,
    longitude: float,
    endereco_aprox: str | None = None,
    descricao: str | None = None,
    categoria: str | None = None,
) -> Alerta:
    alerta = Alerta(
        tipo=TipoAlerta.SOS_FORMULARIO.value,
        id_cidadao=id_cidadao,
        latitude=latitude,
        longitude=longitude,
        endereco_aprox=endereco_aprox,
        descricao=descricao,
        categoria=categoria,
        estado=EstadoAlerta.PENDENTE.value,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


def criar_alerta_medicacao_nao_cumprida(
    db: Session,
    id_cidadao: int,
    latitude: float,
    longitude: float,
    nome_medicamento: str,
    endereco_aprox: str | None = None,
) -> Alerta:
    """Cria alerta para as autoridades: cidadão ignorou 3 doses consecutivas da medicação."""
    descricao = (
        f"Alerta de medicação: o cidadão não cumpriu com a toma do medicamento «{nome_medicamento}» "
        "por 3 vezes consecutivas. Verificar situação."
    )
    alerta = Alerta(
        tipo=TipoAlerta.MEDICACAO_NAO_CUMPRIDA.value,
        id_cidadao=id_cidadao,
        latitude=latitude,
        longitude=longitude,
        endereco_aprox=endereco_aprox,
        descricao=descricao,
        categoria="medicacao_nao_cumprida",
        estado=EstadoAlerta.PENDENTE.value,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


def criar_alerta_familiar(
    db: Session,
    id_cidadao: int,
    id_contato_emergencia: int,
    latitude: float,
    longitude: float,
    mensagem: str | None = None,
) -> AlertaFamiliar:
    af = AlertaFamiliar(
        id_cidadao=id_cidadao,
        id_contato_emergencia=id_contato_emergencia,
        latitude=latitude,
        longitude=longitude,
        mensagem=mensagem,
    )
    db.add(af)
    db.commit()
    db.refresh(af)
    return af


def listar_alertas(
    db: Session,
    estado: str | None = None,
    tipo: str | None = None,
    id_cidadao: int | None = None,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(Alerta)
    if estado:
        q = q.filter(Alerta.estado == estado)
    if tipo:
        q = q.filter(Alerta.tipo == tipo)
    if id_cidadao is not None:
        q = q.filter(Alerta.id_cidadao == id_cidadao)
    return q.order_by(Alerta.created_at.desc()).offset(skip).limit(limit).all()


def obter_alerta(db: Session, id_alerta: int) -> Alerta | None:
    return db.query(Alerta).filter(Alerta.id == id_alerta).first()


def atribuir_autoridade(db: Session, id_alerta: int, id_autoridade: int) -> Alerta | None:
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    alerta.id_autoridade_atribuida = id_autoridade
    alerta.estado = EstadoAlerta.EM_ATENDIMENTO.value
    db.commit()
    db.refresh(alerta)
    return alerta


def atualizar_estado(db: Session, id_alerta: int, estado: str, motivo: str | None = None) -> Alerta | None:
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    alerta.estado = estado
    if estado == EstadoAlerta.CANCELADO.value:
        alerta.cancelado_at = datetime.now(timezone.utc)
        if motivo:
            alerta.motivo_cancelamento = motivo
    elif estado == EstadoAlerta.RESOLVIDO.value:
        alerta.resolvido_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alerta)
    return alerta


def pode_cancelar_pelo_cidadao(alerta: Alerta) -> bool:
    """True se ainda estiver na janela de 20 segundos para o cidadão cancelar."""
    if alerta.estado not in _estados_ativos():
        return False
    if not alerta.created_at:
        return False
    agora = datetime.now(timezone.utc)
    criado = alerta.created_at if alerta.created_at.tzinfo else alerta.created_at.replace(tzinfo=timezone.utc)
    return (agora - criado).total_seconds() <= JANELA_CANCELAMENTO_SEGUNDOS


def cancelar_alerta(
    db: Session,
    id_alerta: int,
    motivo: str,
    id_cidadao: int | None,
    device_id: str | None = None,
    e_admin: bool = False,
) -> Alerta | None:
    """Cancela o alerta. Cidadão só pode nos primeiros 20s com motivo; anónimo exige device_id; admin pode sempre."""
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    if alerta.estado not in _estados_ativos():
        return None
    if e_admin:
        alerta.estado = EstadoAlerta.CANCELADO.value
        alerta.motivo_cancelamento = motivo or "Cancelado pela autoridade"
        alerta.cancelado_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alerta)
        return alerta
    if alerta.id_cidadao is not None:
        if alerta.id_cidadao != id_cidadao:
            return None
    else:
        # Anónimo: só pode cancelar se device_id coincidir com o do alerta
        if not device_id or not str(device_id).strip() or alerta.sessao_anonima != device_id.strip():
            return None
    if not pode_cancelar_pelo_cidadao(alerta):
        return None
    alerta.estado = EstadoAlerta.CANCELADO.value
    alerta.motivo_cancelamento = motivo or "Cancelado pelo utilizador"
    alerta.cancelado_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alerta)
    return alerta


def detalhar_alerta(
    db: Session,
    id_alerta: int,
    id_cidadao: int,
    autoridade_destino: str,
    tipo_ocorrencia: str,
    descricao: str | None = None,
) -> Alerta | None:
    """Converte um SOS rápido do cidadão em SOS detalhado (formulário). Só para alertas ativos e dono."""
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    if alerta.id_cidadao != id_cidadao:
        return None
    if alerta.estado not in _estados_ativos():
        return None
    if alerta.tipo != TipoAlerta.SOS_RAPIDO.value:
        return None
    alerta.tipo = TipoAlerta.SOS_FORMULARIO.value
    alerta.autoridade_destino = autoridade_destino
    alerta.tipo_ocorrencia = tipo_ocorrencia
    alerta.descricao = descricao
    alerta.categoria = tipo_ocorrencia
    db.commit()
    db.refresh(alerta)
    return alerta


def atualizar_localizacao_alerta(
    db: Session,
    id_alerta: int,
    latitude: float,
    longitude: float,
    id_cidadao: int | None,
    device_id: str | None = None,
) -> Alerta | None:
    """Atualiza a última localização do alerta (streaming). Só para dono do alerta (cidadão ou device_id).
    Se o alerta já foi cancelado/resolvido pela autoridade, devolve o alerta na mesma (sem atualizar
    localização) para o app poder gravar e enviar o vídeo antes de sair do modo ocorrência."""
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    if alerta.id_cidadao is not None:
        if alerta.id_cidadao != id_cidadao:
            return None
    else:
        if not device_id or not str(device_id).strip() or alerta.sessao_anonima != device_id.strip():
            return None
    if alerta.estado not in _estados_ativos():
        return alerta
    alerta.ultima_latitude = latitude
    alerta.ultima_longitude = longitude
    alerta.ultima_localizacao_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alerta)
    return alerta


def criar_midia_relatorio(db: Session, id_alerta: int, url_path: str) -> MidiaOcorrencia | None:
    """Regista vídeo de relatório da ocorrência (gravação câmara+mic durante o SOS)."""
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    midia = MidiaOcorrencia(id_alerta=id_alerta, tipo="video", url_path=url_path)
    db.add(midia)
    db.commit()
    db.refresh(midia)
    return midia


def listar_midias_alerta(db: Session, id_alerta: int) -> list:
    """Lista todas as mídias (vídeos, imagens) associadas a um alerta."""
    return (
        db.query(MidiaOcorrencia)
        .filter(MidiaOcorrencia.id_alerta == id_alerta)
        .order_by(MidiaOcorrencia.created_at.asc())
        .all()
    )
