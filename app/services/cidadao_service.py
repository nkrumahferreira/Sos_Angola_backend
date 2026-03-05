from sqlalchemy.orm import Session
from app.models.models import Cidadao, ContatoEmergencia


def obter_cidadao(db: Session, id_cidadao: int) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.id == id_cidadao).first()


def obter_cidadao_por_telefone(db: Session, telefone: str) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.telefone == telefone).first()


def obter_cidadao_por_email(db: Session, email: str) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.email == email).first()


def atualizar_perfil(db: Session, id_cidadao: int, nome: str | None = None, idade: int | None = None) -> Cidadao | None:
    c = obter_cidadao(db, id_cidadao)
    if not c:
        return None
    if nome is not None:
        c.nome = nome
    if idade is not None:
        c.idade = idade
    db.commit()
    db.refresh(c)
    return c


def adicionar_contato_emergencia(
    db: Session,
    id_cidadao: int,
    nome: str,
    telefone: str,
    email: str | None = None,
) -> ContatoEmergencia:
    contato = ContatoEmergencia(
        id_cidadao=id_cidadao,
        nome=nome,
        telefone=telefone,
        email=email,
    )
    db.add(contato)
    db.commit()
    db.refresh(contato)
    return contato


def listar_contatos_emergencia(db: Session, id_cidadao: int):
    return db.query(ContatoEmergencia).filter(
        ContatoEmergencia.id_cidadao == id_cidadao,
        ContatoEmergencia.ativo == True,
    ).all()


def remover_contato_emergencia(db: Session, id_contato: int, id_cidadao: int) -> bool:
    c = db.query(ContatoEmergencia).filter(
        ContatoEmergencia.id == id_contato,
        ContatoEmergencia.id_cidadao == id_cidadao,
    ).first()
    if not c:
        return False
    c.ativo = False
    db.commit()
    return True
