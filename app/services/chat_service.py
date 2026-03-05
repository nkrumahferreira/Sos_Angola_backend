from sqlalchemy.orm import Session
from app.models.models import ChatConversa, ChatMensagem


def obter_ou_criar_conversa(
    db: Session,
    id_cidadao: int,
    id_alerta: int | None = None,
    id_autoridade_user: int | None = None,
) -> ChatConversa:
    conv = db.query(ChatConversa).filter(
        ChatConversa.id_cidadao == id_cidadao,
        ChatConversa.id_alerta == id_alerta,
    ).first()
    if conv:
        return conv
    conv = ChatConversa(
        id_cidadao=id_cidadao,
        id_alerta=id_alerta,
        id_autoridade_user=id_autoridade_user,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def enviar_mensagem(
    db: Session,
    id_conversa: int,
    enviado_por: str,
    id_autor: int | None,
    conteudo: str,
) -> ChatMensagem:
    msg = ChatMensagem(
        id_conversa=id_conversa,
        enviado_por=enviado_por,
        id_autor=id_autor,
        conteudo=conteudo,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def listar_mensagens(db: Session, id_conversa: int, skip: int = 0, limit: int = 100):
    return db.query(ChatMensagem).filter(
        ChatMensagem.id_conversa == id_conversa,
    ).order_by(ChatMensagem.created_at.asc()).offset(skip).limit(limit).all()


def listar_conversas_cidadao(db: Session, id_cidadao: int):
    return db.query(ChatConversa).filter(ChatConversa.id_cidadao == id_cidadao).all()
