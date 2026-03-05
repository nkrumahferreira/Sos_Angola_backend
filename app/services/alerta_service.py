from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import Alerta, AlertaFamiliar, Cidadao, ContatoEmergencia, EstadoAlerta, TipoAlerta


def criar_sos_rapido(
    db: Session,
    latitude: float,
    longitude: float,
    endereco_aprox: str | None = None,
    id_cidadao: int | None = None,
) -> Alerta:
    alerta = Alerta(
        tipo=TipoAlerta.SOS_RAPIDO.value,
        id_cidadao=id_cidadao,
        latitude=latitude,
        longitude=longitude,
        endereco_aprox=endereco_aprox,
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


def atualizar_estado(db: Session, id_alerta: int, estado: str) -> Alerta | None:
    alerta = obter_alerta(db, id_alerta)
    if not alerta:
        return None
    alerta.estado = estado
    db.commit()
    db.refresh(alerta)
    return alerta
