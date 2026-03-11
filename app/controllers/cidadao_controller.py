"""
Perfil do cidadão, contactos de emergência, cuidados especiais e medicação (app mobile).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.database import get_db
from app.schemas.cidadao import (
    CidadaoPerfilUpdate,
    CidadaoPerfilResponse,
    ContatoEmergenciaCreate,
    ContatoEmergenciaUpdate,
    ContatoEmergenciaResponse,
    CuidadosEspeciaisCreate,
    CuidadosEspeciaisUpdate,
    CuidadosEspeciaisResponse,
    MedicacaoCreate,
    MedicacaoResponse,
    RegistarDoseIgnoradaRequest,
)
from app.schemas.alerta import AlertaResponse
from app.dependencies.auth import get_current_user_id
from app.services.cidadao_service import (
    obter_cidadao,
    obter_foto_perfil,
    atualizar_perfil,
    adicionar_contato_emergencia,
    listar_contatos_emergencia,
    remover_contato_emergencia,
    atualizar_contato_emergencia,
    obter_cuidados_especiais,
    criar_ou_atualizar_cuidados_especiais,
    adicionar_medicacao,
    listar_medicacoes,
    remover_medicacao,
    marcar_toma_medicacao,
    registrar_dose_ignorada,
)
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/cidadao", tags=["Cidadão"])


def _foto_url_se_tiver(c) -> str | None:
    """Retorna path da foto para o app carregar (GET /cidadao/me/foto) se tiver fotografia_base64."""
    if getattr(c, "fotografia_base64", None):
        return "/cidadao/me/foto"
    return c.fotografia_url


@router.get("/perfil", response_model=CidadaoPerfilResponse)
def obter_perfil(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    c = obter_cidadao(db, id_cidadao)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cidadão não encontrado.")
    contatos = listar_contatos_emergencia(db, id_cidadao)
    return CidadaoPerfilResponse(
        id=c.id,
        nome=c.nome,
        data_nascimento=c.data_nascimento,
        telefone=c.telefone,
        bi=c.bi,
        email=c.email,
        fotografia_url=_foto_url_se_tiver(c),
        genero=c.genero,
        precisa_cuidados_especiais=c.precisa_cuidados_especiais or False,
        created_at=c.created_at,
        contatos_emergencia=[ContatoEmergenciaResponse.model_validate(co) for co in contatos],
    )


@router.get("/me/foto")
def obter_minha_foto(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    """Retorna a foto de perfil do cidadão autenticado (JPEG). 404 se não tiver."""
    result = obter_foto_perfil(db, id_cidadao)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sem foto de perfil.")
    data, content_type = result
    return Response(content=data, media_type=content_type)


@router.patch("/perfil", response_model=CidadaoPerfilResponse)
def atualizar_perfil_endpoint(
    data: CidadaoPerfilUpdate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    c = atualizar_perfil(
        db,
        id_cidadao,
        nome=data.nome,
        data_nascimento=data.data_nascimento,
        email=data.email,
        fotografia_url=data.fotografia_url,
        fotografia_base64=data.fotografia_base64,
        genero=data.genero,
        precisa_cuidados_especiais=data.precisa_cuidados_especiais,
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cidadão não encontrado.")
    contatos = listar_contatos_emergencia(db, id_cidadao)
    return CidadaoPerfilResponse(
        id=c.id,
        nome=c.nome,
        data_nascimento=c.data_nascimento,
        telefone=c.telefone,
        bi=c.bi,
        email=c.email,
        fotografia_url=_foto_url_se_tiver(c),
        genero=c.genero,
        precisa_cuidados_especiais=c.precisa_cuidados_especiais or False,
        created_at=c.created_at,
        contatos_emergencia=[ContatoEmergenciaResponse.model_validate(co) for co in contatos],
    )


# --- Contatos de emergência ---
@router.post("/contatos-emergencia", response_model=ContatoEmergenciaResponse, status_code=status.HTTP_201_CREATED)
def adicionar_contato(
    data: ContatoEmergenciaCreate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    contato = adicionar_contato_emergencia(
        db, id_cidadao, nome=data.nome, telefone=data.telefone, email=data.email, tipo=data.tipo
    )
    return ContatoEmergenciaResponse.model_validate(contato)


@router.get("/contatos-emergencia", response_model=list[ContatoEmergenciaResponse])
def listar_contatos(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    contatos = listar_contatos_emergencia(db, id_cidadao)
    return [ContatoEmergenciaResponse.model_validate(c) for c in contatos]


@router.patch("/contatos-emergencia/{id_contato}", response_model=ContatoEmergenciaResponse)
def atualizar_contato(
    id_contato: int,
    data: ContatoEmergenciaUpdate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    contato = atualizar_contato_emergencia(
        db, id_contato, id_cidadao, tipo=data.tipo
    )
    if not contato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto não encontrado.")
    return ContatoEmergenciaResponse.model_validate(contato)


@router.delete("/contatos-emergencia/{id_contato}")
def remover_contato(
    id_contato: int,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    if not remover_contato_emergencia(db, id_contato, id_cidadao):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto não encontrado.")
    return {"message": "Contacto removido."}


# --- Cuidados especiais ---
@router.get("/cuidados-especiais", response_model=CuidadosEspeciaisResponse | None)
def obter_cuidados(db=Depends(get_db), id_cidadao: int = Depends(get_current_user_id)):
    ce = obter_cuidados_especiais(db, id_cidadao)
    if not ce:
        return None
    medicacoes = listar_medicacoes(db, ce.id)
    return CuidadosEspeciaisResponse(
        id=ce.id,
        id_cidadao=ce.id_cidadao,
        tipo_paciente=ce.tipo_paciente,
        doencas_conhecidas=ce.doencas_conhecidas,
        alergias=ce.alergias,
        tipo_sanguineo=ce.tipo_sanguineo,
        id_medico_responsavel=ce.id_medico_responsavel,
        hospital_ou_clinica=ce.hospital_ou_clinica,
        id_cuidador=ce.id_cuidador,
        medicacoes=[MedicacaoResponse.model_validate(m) for m in medicacoes],
    )


@router.put("/cuidados-especiais", response_model=CuidadosEspeciaisResponse)
def salvar_cuidados_especiais(
    data: CuidadosEspeciaisCreate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    try:
        medicacoes = None
        if data.medicacoes is not None:
            medicacoes = [m.model_dump() for m in data.medicacoes]
        ce = criar_ou_atualizar_cuidados_especiais(
            db,
            id_cidadao,
            tipo_paciente=data.tipo_paciente,
            doencas_conhecidas=data.doencas_conhecidas,
            alergias=data.alergias,
            tipo_sanguineo=data.tipo_sanguineo,
            id_medico_responsavel=data.id_medico_responsavel,
            hospital_ou_clinica=data.hospital_ou_clinica,
            id_cuidador=data.id_cuidador,
            medicacoes=medicacoes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    medicacoes_list = listar_medicacoes(db, ce.id)
    return CuidadosEspeciaisResponse(
        id=ce.id,
        id_cidadao=ce.id_cidadao,
        tipo_paciente=ce.tipo_paciente,
        doencas_conhecidas=ce.doencas_conhecidas,
        alergias=ce.alergias,
        tipo_sanguineo=ce.tipo_sanguineo,
        id_medico_responsavel=ce.id_medico_responsavel,
        hospital_ou_clinica=ce.hospital_ou_clinica,
        id_cuidador=ce.id_cuidador,
        medicacoes=[MedicacaoResponse.model_validate(m) for m in medicacoes_list],
    )


@router.patch("/cuidados-especiais", response_model=CuidadosEspeciaisResponse)
def atualizar_cuidados_especiais(
    data: CuidadosEspeciaisUpdate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    try:
        ce = criar_ou_atualizar_cuidados_especiais(
            db,
            id_cidadao,
            tipo_paciente=data.tipo_paciente,
            doencas_conhecidas=data.doencas_conhecidas,
            alergias=data.alergias,
            tipo_sanguineo=data.tipo_sanguineo,
            id_medico_responsavel=data.id_medico_responsavel,
            hospital_ou_clinica=data.hospital_ou_clinica,
            id_cuidador=data.id_cuidador,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    medicacoes_list = listar_medicacoes(db, ce.id)
    return CuidadosEspeciaisResponse(
        id=ce.id,
        id_cidadao=ce.id_cidadao,
        tipo_paciente=ce.tipo_paciente,
        doencas_conhecidas=ce.doencas_conhecidas,
        alergias=ce.alergias,
        tipo_sanguineo=ce.tipo_sanguineo,
        id_medico_responsavel=ce.id_medico_responsavel,
        hospital_ou_clinica=ce.hospital_ou_clinica,
        id_cuidador=ce.id_cuidador,
        medicacoes=[MedicacaoResponse.model_validate(m) for m in medicacoes_list],
    )


# --- Medicação (dentro de cuidados especiais) ---
@router.post("/cuidados-especiais/medicacoes", response_model=MedicacaoResponse, status_code=status.HTTP_201_CREATED)
def adicionar_medicacao_endpoint(
    data: MedicacaoCreate,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    ce = obter_cuidados_especiais(db, id_cidadao)
    if not ce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crie primeiro o registo de cuidados especiais (perfil com precisa_cuidados_especiais=True).",
        )
    med = adicionar_medicacao(
        db,
        ce.id,
        nome_medicamento=data.nome_medicamento,
        dosagem=data.dosagem,
        horario_tomar=data.horario_tomar,
        frequencia_monitorizacao=data.frequencia_monitorizacao,
        dose_valor=data.dose_valor,
        dose_unidade=data.dose_unidade,
        tipo_frequencia=data.tipo_frequencia,
        intervalo_horas=data.intervalo_horas,
        intervalo_dias=data.intervalo_dias,
        dias_semana=data.dias_semana,
        horario_fixo=data.horario_fixo,
    )
    return MedicacaoResponse.model_validate(med)


@router.post("/cuidados-especiais/medicacoes/{id_medicacao}/tomar", response_model=MedicacaoResponse)
def marcar_toma_medicacao_endpoint(
    id_medicacao: int,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Regista que o paciente tomou a dose agora. Para tipo 'intervalo', calcula a próxima dose (ex.: tomou às 14h, de 8 em 8h → próxima 22h)."""
    ce = obter_cuidados_especiais(db, id_cidadao)
    if not ce:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuidados especiais não encontrados.")
    med = marcar_toma_medicacao(db, id_medicacao, ce.id)
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento não encontrado.")
    return MedicacaoResponse.model_validate(med)


@router.post("/cuidados-especiais/medicacoes/{id_medicacao}/registar-ignorada")
async def registar_dose_ignorada_endpoint(
    id_medicacao: int,
    data: RegistarDoseIgnoradaRequest,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Regista que o paciente não tomou a dose (ignorada). Se for a 3.ª vez consecutiva, emite alerta às autoridades."""
    ce = obter_cuidados_especiais(db, id_cidadao)
    if not ce:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuidados especiais não encontrados.")
    med, alerta = registrar_dose_ignorada(
        db,
        id_medicacao=id_medicacao,
        id_cuidados_especiais=ce.id,
        id_cidadao=id_cidadao,
        latitude=data.latitude,
        longitude=data.longitude,
        endereco_aprox=data.endereco_aprox,
    )
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento não encontrado.")
    result = {
        "medicacao": MedicacaoResponse.model_validate(med),
        "alerta_emitido": alerta is not None,
    }
    if alerta:
        result["alerta"] = AlertaResponse.model_validate(alerta)
        await ws_manager.broadcast_alertas({"evento": "novo_alerta", "alerta": result["alerta"].model_dump(mode="json")})
    return result


@router.delete("/cuidados-especiais/medicacoes/{id_medicacao}")
def remover_medicacao_endpoint(
    id_medicacao: int,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    ce = obter_cuidados_especiais(db, id_cidadao)
    if not ce:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuidados especiais não encontrados.")
    if not remover_medicacao(db, id_medicacao, ce.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento não encontrado.")
    return {"message": "Medicamento removido."}
