import json
from sqlalchemy.orm import Session
from datetime import date, datetime, timezone, timedelta
from app.models.models import Alerta, Cidadao, ContatoEmergencia, CuidadosEspeciais, MedicacaoCidadao
from app.services.alerta_service import criar_alerta_medicacao_nao_cumprida
from app.services.whatsapp_service import (
    enviar_whatsapp,
    formatar_mensagem_alerta_3_ignoradas,
    formatar_mensagem_horarios_medicacao,
)


def obter_cidadao(db: Session, id_cidadao: int) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.id == id_cidadao).first()


def obter_cidadao_por_telefone(db: Session, telefone: str) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.telefone == telefone).first()


def obter_cidadao_por_email(db: Session, email: str) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.email == email).first()


def obter_cidadao_por_bi(db: Session, bi: str) -> Cidadao | None:
    return db.query(Cidadao).filter(Cidadao.bi == bi).first()


def obter_foto_perfil(db: Session, id_cidadao: int) -> tuple[bytes, str] | None:
    """Retorna (bytes da imagem, content_type) ou None se não tiver foto."""
    c = obter_cidadao(db, id_cidadao)
    if not c or not getattr(c, "fotografia_base64", None):
        return None
    import base64
    try:
        b64 = c.fotografia_base64
        if b64.startswith("data:"):
            # data:image/jpeg;base64,XXXX
            parts = b64.split(",", 1)
            b64 = parts[1] if len(parts) > 1 else b64
        data = base64.b64decode(b64)
        return (data, "image/jpeg")
    except Exception:
        return None


def atualizar_perfil(
    db: Session,
    id_cidadao: int,
    nome: str | None = None,
    data_nascimento: date | None = None,
    email: str | None = None,
    fotografia_url: str | None = None,
    fotografia_base64: str | None = None,
    genero: str | None = None,
    precisa_cuidados_especiais: bool | None = None,
) -> Cidadao | None:
    c = obter_cidadao(db, id_cidadao)
    if not c:
        return None
    if nome is not None:
        c.nome = nome
    if data_nascimento is not None:
        c.data_nascimento = data_nascimento
    if email is not None:
        c.email = email
    if fotografia_url is not None:
        c.fotografia_url = fotografia_url
    if fotografia_base64 is not None:
        c.fotografia_base64 = fotografia_base64
    if genero is not None:
        c.genero = genero
    if precisa_cuidados_especiais is not None:
        c.precisa_cuidados_especiais = precisa_cuidados_especiais
    db.commit()
    db.refresh(c)
    return c


def adicionar_contato_emergencia(
    db: Session,
    id_cidadao: int,
    nome: str,
    telefone: str,
    email: str | None = None,
    tipo: str | None = None,
) -> ContatoEmergencia:
    contato = ContatoEmergencia(
        id_cidadao=id_cidadao,
        nome=nome,
        telefone=telefone,
        email=email,
        tipo=tipo,
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


def atualizar_contato_emergencia(
    db: Session,
    id_contato: int,
    id_cidadao: int,
    tipo: str | None = None,
) -> ContatoEmergencia | None:
    c = db.query(ContatoEmergencia).filter(
        ContatoEmergencia.id == id_contato,
        ContatoEmergencia.id_cidadao == id_cidadao,
        ContatoEmergencia.ativo == True,
    ).first()
    if not c:
        return None
    if tipo is not None:
        c.tipo = tipo
    db.commit()
    db.refresh(c)
    return c


# --- Cuidados especiais ---
def obter_cuidados_especiais(db: Session, id_cidadao: int) -> CuidadosEspeciais | None:
    return db.query(CuidadosEspeciais).filter(CuidadosEspeciais.id_cidadao == id_cidadao).first()


def criar_ou_atualizar_cuidados_especiais(
    db: Session,
    id_cidadao: int,
    tipo_paciente: str | None = None,
    doencas_conhecidas: str | None = None,
    alergias: str | None = None,
    tipo_sanguineo: str | None = None,
    id_medico_responsavel: int | None = None,
    hospital_ou_clinica: str | None = None,
    id_cuidador: int | None = None,
    medicacoes: list[dict] | None = None,
) -> CuidadosEspeciais:
    """Cria ou atualiza o registo de cuidados especiais do cidadão. medicacoes = list of {nome_medicamento, dosagem, horario_tomar, frequencia_monitorizacao}."""
    cidadao = obter_cidadao(db, id_cidadao)
    if not cidadao:
        raise ValueError("Cidadão não encontrado.")
    existente = obter_cuidados_especiais(db, id_cidadao)
    if existente:
        if tipo_paciente is not None:
            existente.tipo_paciente = tipo_paciente
        if doencas_conhecidas is not None:
            existente.doencas_conhecidas = doencas_conhecidas
        if alergias is not None:
            existente.alergias = alergias
        if tipo_sanguineo is not None:
            existente.tipo_sanguineo = tipo_sanguineo
        if id_medico_responsavel is not None:
            existente.id_medico_responsavel = id_medico_responsavel
        if hospital_ou_clinica is not None:
            existente.hospital_ou_clinica = hospital_ou_clinica
        if id_cuidador is not None:
            existente.id_cuidador = id_cuidador
        db.commit()
        db.refresh(existente)
        ce = existente
    else:
        ce = CuidadosEspeciais(
            id_cidadao=id_cidadao,
            tipo_paciente=tipo_paciente,
            doencas_conhecidas=doencas_conhecidas,
            alergias=alergias,
            tipo_sanguineo=tipo_sanguineo,
            id_medico_responsavel=id_medico_responsavel,
            hospital_ou_clinica=hospital_ou_clinica,
            id_cuidador=id_cuidador,
        )
        db.add(ce)
        db.commit()
        db.refresh(ce)
    if medicacoes is not None:
        # Remover medicacoes antigas e inserir as novas
        db.query(MedicacaoCidadao).filter(MedicacaoCidadao.id_cuidados_especiais == ce.id).delete()
        for m in medicacoes:
            med = MedicacaoCidadao(
                id_cuidados_especiais=ce.id,
                nome_medicamento=m.get("nome_medicamento", ""),
                dosagem=m.get("dosagem"),
                horario_tomar=m.get("horario_tomar"),
                frequencia_monitorizacao=m.get("frequencia_monitorizacao"),
            )
            db.add(med)
        db.commit()
        db.refresh(ce)
    return ce


def _serialize_json(value) -> str | None:
    if value is None:
        return None
    import json
    return json.dumps(value)


def adicionar_medicacao(
    db: Session,
    id_cuidados_especiais: int,
    nome_medicamento: str,
    dosagem: str | None = None,
    horario_tomar: str | None = None,
    frequencia_monitorizacao: str | None = None,
    dose_valor: float | None = None,
    dose_unidade: str | None = None,
    tipo_frequencia: str | None = None,
    intervalo_horas: int | None = None,
    intervalo_dias: int | None = None,
    dias_semana: list | None = None,
    horario_fixo: str | None = None,
) -> MedicacaoCidadao:
    med = MedicacaoCidadao(
        id_cuidados_especiais=id_cuidados_especiais,
        nome_medicamento=nome_medicamento,
        dosagem=dosagem,
        horario_tomar=horario_tomar,
        frequencia_monitorizacao=frequencia_monitorizacao,
        dose_valor=dose_valor,
        dose_unidade=dose_unidade,
        tipo_frequencia=tipo_frequencia,
        intervalo_horas=intervalo_horas,
        intervalo_dias=intervalo_dias,
        dias_semana=_serialize_json(dias_semana),
        horario_fixo=horario_fixo,
        estado_atual="pendente",
        historico_doses=_serialize_json([]),
    )
    if tipo_frequencia == "intervalo" and intervalo_horas:
        now = datetime.now(timezone.utc)
        med.ultima_dose = None
        med.proxima_dose = now + timedelta(hours=intervalo_horas)
    db.add(med)
    db.commit()
    db.refresh(med)
    # Enviar horários de medicação ao cuidador por WhatsApp
    ce = db.query(CuidadosEspeciais).filter(CuidadosEspeciais.id == id_cuidados_especiais).first()
    if ce and ce.id_cuidador:
        cuidador = db.query(ContatoEmergencia).filter(ContatoEmergencia.id == ce.id_cuidador).first()
        if cuidador and cuidador.telefone:
            cidadao = obter_cidadao(db, ce.id_cidadao)
            medicacoes = listar_medicacoes(db, id_cuidados_especiais)
            if cidadao and medicacoes:
                msg = formatar_mensagem_horarios_medicacao(
                    cidadao.nome or "Paciente",
                    medicacoes,
                    nome_contato_emergencia=getattr(cuidador, "nome", None),
                )
                enviar_whatsapp(cuidador.telefone, msg)
    return med


def listar_medicacoes(db: Session, id_cuidados_especiais: int):
    return db.query(MedicacaoCidadao).filter(MedicacaoCidadao.id_cuidados_especiais == id_cuidados_especiais).all()


def remover_medicacao(db: Session, id_medicacao: int, id_cuidados_especiais: int) -> bool:
    m = db.query(MedicacaoCidadao).filter(
        MedicacaoCidadao.id == id_medicacao,
        MedicacaoCidadao.id_cuidados_especiais == id_cuidados_especiais,
    ).first()
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True


def marcar_toma_medicacao(
    db: Session,
    id_medicacao: int,
    id_cuidados_especiais: int,
    data_hora_toma: datetime | None = None,
) -> MedicacaoCidadao | None:
    """Regista que o paciente tomou a dose. Atualiza ultima_dose, historico_doses e calcula proxima_dose (para tipo intervalo)."""
    m = db.query(MedicacaoCidadao).filter(
        MedicacaoCidadao.id == id_medicacao,
        MedicacaoCidadao.id_cuidados_especiais == id_cuidados_especiais,
    ).first()
    if not m:
        return None
    now = data_hora_toma or datetime.now(timezone.utc)
    m.ultima_dose = now
    m.estado_atual = "tomado"
    historico = []
    if m.historico_doses:
        try:
            historico = json.loads(m.historico_doses)
        except (TypeError, json.JSONDecodeError):
            pass
    historico.append({"data_hora": now.isoformat(), "estado": "tomado"})
    m.historico_doses = json.dumps(historico)
    if m.tipo_frequencia == "intervalo" and m.intervalo_horas:
        m.proxima_dose = now + timedelta(hours=m.intervalo_horas)
        m.estado_atual = "pendente"
    db.commit()
    db.refresh(m)
    return m


def registrar_dose_ignorada(
    db: Session,
    id_medicacao: int,
    id_cuidados_especiais: int,
    id_cidadao: int,
    latitude: float,
    longitude: float,
    endereco_aprox: str | None = None,
) -> tuple[MedicacaoCidadao | None, Alerta | None]:
    """Regista que o paciente não tomou a dose (ignorada). Adiciona ao histórico.
    Se as últimas 3 entradas forem 'ignorado', cria um alerta para as autoridades.
    Retorna (medicacao, alerta ou None)."""
    m = db.query(MedicacaoCidadao).filter(
        MedicacaoCidadao.id == id_medicacao,
        MedicacaoCidadao.id_cuidados_especiais == id_cuidados_especiais,
    ).first()
    if not m:
        return None, None
    ce = db.query(CuidadosEspeciais).filter(CuidadosEspeciais.id == id_cuidados_especiais).first()
    if not ce or ce.id_cidadao != id_cidadao:
        return None, None

    now = datetime.now(timezone.utc)
    data_hora_ignorada = m.proxima_dose if m.proxima_dose and m.proxima_dose <= now else now

    historico = []
    if m.historico_doses:
        try:
            historico = json.loads(m.historico_doses)
        except (TypeError, json.JSONDecodeError):
            pass
    historico.append({"data_hora": data_hora_ignorada.isoformat(), "estado": "ignorado"})
    m.historico_doses = json.dumps(historico)
    m.estado_atual = "ignorado"

    # Calcular próxima dose
    if m.tipo_frequencia == "intervalo" and m.intervalo_horas:
        ref = m.proxima_dose if m.proxima_dose else now
        m.proxima_dose = ref + timedelta(hours=m.intervalo_horas)
        m.estado_atual = "pendente"
    else:
        m.proxima_dose = now + timedelta(hours=24)
        m.estado_atual = "pendente"

    db.commit()
    db.refresh(m)

    # Verificar se as últimas 3 são "ignorado"
    ultimas = historico[-3:] if len(historico) >= 3 else []
    if len(ultimas) == 3 and all(e.get("estado") == "ignorado" for e in ultimas):
        alerta = criar_alerta_medicacao_nao_cumprida(
            db,
            id_cidadao=id_cidadao,
            latitude=latitude,
            longitude=longitude,
            nome_medicamento=m.nome_medicamento,
            endereco_aprox=endereco_aprox,
        )
        # Notificar cuidador por WhatsApp
        ce = db.query(CuidadosEspeciais).filter(CuidadosEspeciais.id == id_cuidados_especiais).first()
        if ce and ce.id_cuidador:
            cuidador = db.query(ContatoEmergencia).filter(ContatoEmergencia.id == ce.id_cuidador).first()
            cidadao = obter_cidadao(db, id_cidadao)
            if cuidador and cuidador.telefone and cidadao:
                msg = formatar_mensagem_alerta_3_ignoradas(cidadao.nome, m.nome_medicamento)
                enviar_whatsapp(cuidador.telefone, msg)
        return m, alerta
    return m, None


def verificar_e_registar_doses_ignoradas(db: Session) -> list:
    """
    Job em background: encontra todas as medicações com proxima_dose no passado e
    estado_atual='pendente', regista cada uma como dose ignorada (com lat=0, lon=0).
    Devolve a lista de alertas criados (3.ª ignorada consecutiva).
    Assim as doses são registadas como ignoradas mesmo que o utilizador não abra a app.
    """
    now = datetime.now(timezone.utc)
    # Medicações com próxima dose já passada e ainda pendentes
    atrasadas = (
        db.query(MedicacaoCidadao)
        .join(CuidadosEspeciais, MedicacaoCidadao.id_cuidados_especiais == CuidadosEspeciais.id)
        .filter(
            MedicacaoCidadao.proxima_dose <= now,
            MedicacaoCidadao.estado_atual == "pendente",
        )
        .all()
    )
    alertas_criados = []
    for m in atrasadas:
        ce = db.query(CuidadosEspeciais).filter(CuidadosEspeciais.id == m.id_cuidados_especiais).first()
        if not ce:
            continue
        _, alerta = registrar_dose_ignorada(
            db,
            id_medicacao=m.id,
            id_cuidados_especiais=m.id_cuidados_especiais,
            id_cidadao=ce.id_cidadao,
            latitude=0.0,
            longitude=0.0,
            endereco_aprox="Registo automático (utilizador não abriu a app)",
        )
        if alerta:
            alertas_criados.append(alerta)
    return alertas_criados
