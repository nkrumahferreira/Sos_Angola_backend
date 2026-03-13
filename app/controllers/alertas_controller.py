"""
Alertas: SOS rápido (público/anónimo), SOS formulário e alerta familiar (logado).
Dashboard: listar, atribuir autoridade, atualizar estado.
Upload de relatório vídeo (gravação câmara+mic durante a ocorrência).
"""
import logging
import subprocess
import uuid
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query, File, UploadFile, Form

from app.config import settings
from app.database import get_db, get_session_local
from app.models.models import MidiaOcorrencia
from app.schemas.alerta import (
    SOSRapidoRequest,
    SOSFormularioRequest,
    AlertaFamiliarRequest,
    AlertaResponse,
    AlertaAtribuirAutoridade,
    AlertaEstadoUpdate,
    CancelarAlertaRequest,
    AtualizarLocalizacaoAlertaRequest,
    TransformarFormularioRequest,
    MidiaOcorrenciaResponse,
)
from app.schemas.cidadao import (
    CidadaoParaAutoridadeResponse,
    ContatoEmergenciaResponse,
    CuidadosEspeciaisResponse,
)
from app.dependencies.auth import get_current_user_id_optional, get_current_user_id, require_autoridade
from app.services.alerta_service import (
    criar_sos_rapido,
    criar_sos_formulario,
    criar_alerta_familiar,
    listar_alertas,
    obter_alerta,
    obter_alerta_ativo_cidadao,
    obter_alerta_ativo_por_dispositivo,
    atribuir_autoridade,
    atualizar_estado,
    cancelar_alerta,
    detalhar_alerta,
    atualizar_localizacao_alerta,
    pode_cancelar_pelo_cidadao,
    criar_midia_relatorio,
    listar_midias_alerta,
)
from app.services.cidadao_service import listar_contatos_emergencia, obter_cidadao, obter_cuidados_especiais
from app.services.whatsapp_service import (
    enviar_whatsapp,
    formatar_mensagem_sos_contatos,
    formatar_mensagem_ocorrencia_encerrada,
)
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.get("/meu-alerta-ativo", response_model=AlertaResponse | None)
def meu_alerta_ativo(
    db=Depends(get_db),
    id_cidadao: int | None = Depends(get_current_user_id_optional),
):
    """Cidadão logado: retorna o alerta ativo (pendente ou em_atendimento), ou None."""
    if id_cidadao is None:
        return None
    alerta = obter_alerta_ativo_cidadao(db, id_cidadao)
    return AlertaResponse.model_validate(alerta) if alerta else None


@router.get("/alerta-ativo-anonimo", response_model=AlertaResponse | None)
def alerta_ativo_anonimo(
    device_id: str | None = Query(None, description="Identificador de dispositivo/sessão (anónimos)"),
    db=Depends(get_db),
):
    """Público: retorna o alerta ativo (pendente ou em_atendimento) associado ao device_id, ou None. Para anónimos mostrarem banner e cancelarem."""
    if not device_id or not device_id.strip():
        return None
    alerta = obter_alerta_ativo_por_dispositivo(db, device_id.strip())
    return AlertaResponse.model_validate(alerta) if alerta else None


@router.post("/sos-rapido", response_model=AlertaResponse)
async def sos_rapido(
    data: SOSRapidoRequest,
    db=Depends(get_db),
    id_cidadao: int | None = Depends(get_current_user_id_optional),
):
    """Público: qualquer um pode enviar SOS com localização. Opcional: autoridade (policia, bombeiros, ambulancia) e tipo. Anónimos: device_id obrigatório (um SOS ativo por dispositivo). Logado: notifica contatos de emergência por WhatsApp."""
    try:
        alerta = criar_sos_rapido(
            db,
            latitude=data.latitude,
            longitude=data.longitude,
            endereco_aprox=data.endereco_aprox,
            id_cidadao=id_cidadao,
            device_id=data.device_id,
            autoridade_destino=data.autoridade_destino,
            tipo_ocorrencia=data.tipo_ocorrencia,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    resp = AlertaResponse.model_validate(alerta)
    await ws_manager.broadcast_alertas({"evento": "novo_alerta", "alerta": resp.model_dump(mode="json")})
    if id_cidadao:
        cidadao = obter_cidadao(db, id_cidadao)
        contatos = listar_contatos_emergencia(db, id_cidadao)
        nome = cidadao.nome if cidadao else "Um contacto seu"
        msg = formatar_mensagem_sos_contatos(
            nome,
            endereco_aprox=data.endereco_aprox,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        for c in contatos:
            if c.telefone:
                enviar_whatsapp(c.telefone, msg)
    return resp


@router.post("/sos-formulario", response_model=AlertaResponse)
async def sos_formulario(
    data: SOSFormularioRequest,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Cidadão logado: alerta com formulário + localização."""
    alerta = criar_sos_formulario(
        db,
        id_cidadao=id_cidadao,
        latitude=data.latitude,
        longitude=data.longitude,
        endereco_aprox=data.endereco_aprox,
        descricao=data.descricao,
        categoria=data.categoria,
    )
    resp = AlertaResponse.model_validate(alerta)
    await ws_manager.broadcast_alertas({"evento": "novo_alerta", "alerta": resp.model_dump(mode="json")})
    return resp


@router.post("/alerta-familiar", response_model=dict)
def alerta_familiar(
    data: AlertaFamiliarRequest,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Cidadão logado: envia alerta com localização para um contacto de emergência."""
    contatos = listar_contatos_emergencia(db, id_cidadao)
    if not any(c.id == data.id_contato_emergencia for c in contatos):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto de emergência não encontrado.")
    af = criar_alerta_familiar(
        db,
        id_cidadao=id_cidadao,
        id_contato_emergencia=data.id_contato_emergencia,
        latitude=data.latitude,
        longitude=data.longitude,
        mensagem=data.mensagem,
    )
    return {"id": af.id, "message": "Alerta enviado aos familiares."}


def _notificar_contatos_ocorrencia_encerrada(db, id_cidadao: int, situacao: str, motivo: str | None = None):
    """Envia WhatsApp aos contatos de emergência quando a ocorrência é cancelada ou concluída."""
    if not id_cidadao:
        return
    cidadao = obter_cidadao(db, id_cidadao)
    contatos = listar_contatos_emergencia(db, id_cidadao)
    nome = cidadao.nome if cidadao else "Um contacto seu"
    msg = formatar_mensagem_ocorrencia_encerrada(nome, situacao, motivo)
    for c in contatos:
        if c.telefone:
            enviar_whatsapp(c.telefone, msg)


@router.post("/{alerta_id}/cancelar", response_model=AlertaResponse)
def cancelar_alerta_cidadao(
    alerta_id: int,
    body: CancelarAlertaRequest,
    db=Depends(get_db),
    id_cidadao: int | None = Depends(get_current_user_id_optional),
):
    """Cidadão: cancela o próprio alerta nos primeiros 20 segundos, com motivo. Anónimos: device_id obrigatório."""
    if not body.motivo or not body.motivo.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indique o motivo do cancelamento.")
    if id_cidadao is None and (not body.device_id or not body.device_id.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para utilizadores anónimos é necessário enviar device_id para cancelar o alerta.",
        )
    alerta = cancelar_alerta(db, alerta_id, body.motivo.strip(), id_cidadao, device_id=body.device_id, e_admin=False)
    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não pode cancelar este alerta. Só pode cancelar nos primeiros 20 segundos; após isso apenas a autoridade pode cancelar.",
        )
    if alerta.id_cidadao:
        _notificar_contatos_ocorrencia_encerrada(db, alerta.id_cidadao, "cancelada", alerta.motivo_cancelamento)
    return AlertaResponse.model_validate(alerta)


@router.patch("/{alerta_id}/detalhar", response_model=AlertaResponse)
def transformar_em_formulario(
    alerta_id: int,
    body: TransformarFormularioRequest,
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
):
    """Cidadão logado: converte o seu SOS rápido ativo em SOS detalhado (autoridade + tipo de ocorrência + descrição)."""
    alerta = detalhar_alerta(
        db,
        id_alerta=alerta_id,
        id_cidadao=id_cidadao,
        autoridade_destino=body.autoridade_destino,
        tipo_ocorrencia=body.tipo_ocorrencia,
        descricao=body.descricao,
    )
    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível transformar. Verifique que a ocorrência é sua e está ativa.",
        )
    return AlertaResponse.model_validate(alerta)


async def _broadcast_localizacao_atualizada(
    alerta_id: int,
    ultima_latitude: float,
    ultima_longitude: float,
    ultima_localizacao_at: str | None,
) -> None:
    """Envia ao canal WebSocket 'alertas' para o dashboard atualizar o mapa em tempo real."""
    await ws_manager.broadcast_alertas({
        "evento": "localizacao_atualizada",
        "alerta_id": alerta_id,
        "ultima_latitude": ultima_latitude,
        "ultima_longitude": ultima_longitude,
        "ultima_localizacao_at": ultima_localizacao_at,
    })


@router.patch("/{alerta_id}/localizacao", response_model=AlertaResponse)
def atualizar_localizacao(
    alerta_id: int,
    data: AtualizarLocalizacaoAlertaRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    id_cidadao: int | None = Depends(get_current_user_id_optional),
):
    """Atualiza a localização do alerta (streaming). Só para alertas ativos. Anónimo: device_id obrigatório."""
    if id_cidadao is None and (not data.device_id or not data.device_id.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para utilizadores anónimos é necessário enviar device_id para atualizar a localização.",
        )
    alerta = atualizar_localizacao_alerta(
        db, alerta_id, data.latitude, data.longitude, id_cidadao, device_id=data.device_id
    )
    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta não encontrado ou já não está ativo.",
        )
    ultima_at = alerta.ultima_localizacao_at
    background_tasks.add_task(
        _broadcast_localizacao_atualizada,
        alerta_id,
        alerta.ultima_latitude,
        alerta.ultima_longitude,
        ultima_at.isoformat() if ultima_at else None,
    )
    return AlertaResponse.model_validate(alerta)


ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "mkv"}
MAX_VIDEO_RELATORIO_MB = 500
_log = logging.getLogger(__name__)


def _transcode_video_to_h264(file_path_str: str, midia_id: int, alerta_id: int) -> None:
    """
    Converte o vídeo para H.264 (MP4) em background. Usa caminho absoluto para não depender do cwd.
    Só remove o original depois de atualizar a BD; se ffmpeg falhar, o ficheiro original fica na pasta.
    """
    file_path = Path(file_path_str).resolve()
    if not file_path.is_file():
        _log.warning("Transcode: ficheiro não encontrado %s", file_path)
        return
    if file_path.suffix.lower() == ".mp4":
        out_path = file_path.parent / (file_path.stem + "_h264.mp4")
    else:
        out_path = file_path.parent / (file_path.stem + ".mp4")
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(file_path),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(out_path),
            ],
            capture_output=True,
            timeout=600,
        )
        if proc.returncode != 0:
            _log.warning(
                "Transcode ffmpeg falhou (midia_id=%s): %s",
                midia_id,
                (proc.stderr or b"").decode("utf-8", errors="replace")[-500:],
            )
            return
        if not out_path.is_file():
            return
        new_url_path = f"relatorios/{alerta_id}/{out_path.name}"
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            midia = db.query(MidiaOcorrencia).filter(MidiaOcorrencia.id == midia_id).first()
            if midia:
                midia.url_path = new_url_path
                db.commit()
                _log.info("Vídeo convertido para H.264: %s", new_url_path)
        finally:
            db.close()
        file_path.unlink(missing_ok=True)
    except FileNotFoundError:
        _log.warning("ffmpeg não encontrado. Instale ffmpeg e reinicie o servidor (PATH). O vídeo original foi guardado.")
    except subprocess.TimeoutExpired:
        _log.warning("Transcode timeout (midia_id=%s). O vídeo original foi guardado.", midia_id)
        if out_path.exists():
            out_path.unlink(missing_ok=True)
    except Exception as e:
        _log.exception("Erro ao transcodificar vídeo (midia_id=%s): %s", midia_id, e)
        if out_path.exists():
            out_path.unlink(missing_ok=True)


@router.post("/{alerta_id}/relatorio-video")
async def upload_relatorio_video(
    alerta_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Vídeo da gravação (câmara+mic) da ocorrência"),
    device_id: str | None = Form(None, description="Obrigatório para anónimos"),
    camera: str | None = Query(None, description="Câmara: 'front' (frontal) ou 'back' (traseira). Opcional; sem valor = vídeo único."),
    db=Depends(get_db),
    id_cidadao: int | None = Depends(get_current_user_id_optional),
):
    """Cidadão envia o vídeo-relatório (um ou dois: frontal e/ou traseira). Use camera=front ou camera=back para identificar."""
    alerta = obter_alerta(db, alerta_id)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    if alerta.id_cidadao is not None:
        if id_cidadao is None or alerta.id_cidadao != id_cidadao:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não pode enviar relatório para este alerta.")
    else:
        did = (device_id or "").strip()
        if not did or alerta.sessao_anonima != did:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não pode enviar relatório para este alerta (device_id inválido).")

    ext = (Path(file.filename or "").suffix or ".mp4").lower().lstrip(".")
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        ext = "mp4"
    size_limit = MAX_VIDEO_RELATORIO_MB * 1024 * 1024
    content = await file.read()
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Vídeo demasiado grande. Máximo {MAX_VIDEO_RELATORIO_MB} MB.",
        )

    suffix = ""
    if (camera or "").strip().lower() in ("front", "back"):
        suffix = f"_{camera.strip().lower()}"

    upload_path = settings.get_upload_path().resolve()
    relatorios_dir = upload_path / "relatorios" / str(alerta_id)
    relatorios_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}.{ext}"
    file_path = (relatorios_dir / filename).resolve()
    file_path.write_bytes(content)
    url_path = f"relatorios/{alerta_id}/{filename}"

    midia = criar_midia_relatorio(db, alerta_id, url_path)
    if not midia:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao registar mídia.")

    background_tasks.add_task(_transcode_video_to_h264, str(file_path), midia.id, alerta_id)
    return {"id": midia.id, "url_path": url_path, "message": "Relatório vídeo guardado. A converter para H.264 em background."}


@router.get("/{alerta_id}/pode-cancelar")
def alerta_pode_cancelar(
    alerta_id: int,
    db=Depends(get_db),
):
    """Retorna se o cidadão ainda pode cancelar (janela de 20s)."""
    alerta = obter_alerta(db, alerta_id)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    return {"pode_cancelar": pode_cancelar_pelo_cidadao(alerta)}


@router.get("/meus", response_model=list[AlertaResponse])
def meus_alertas(
    db=Depends(get_db),
    id_cidadao: int = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Cidadão logado: lista os seus alertas."""
    alertas = listar_alertas(db, id_cidadao=id_cidadao, skip=skip, limit=limit)
    return [AlertaResponse.model_validate(a) for a in alertas]


# --- Dashboard autoridades ---
@router.get("/", response_model=list[AlertaResponse])
def listar_alertas_endpoint(
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
    estado: str | None = Query(None),
    tipo: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    alertas = listar_alertas(db, estado=estado, tipo=tipo, skip=skip, limit=limit)
    return [AlertaResponse.model_validate(a) for a in alertas]


@router.get("/cidadao/{id_cidadao}", response_model=CidadaoParaAutoridadeResponse)
def obter_cidadao_para_autoridade(
    id_cidadao: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    """Dashboard: obtém dados do cidadão por ID (perfil, contatos de emergência e cuidados especiais)."""
    c = obter_cidadao(db, id_cidadao)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cidadão não encontrado.")
    contatos = listar_contatos_emergencia(db, id_cidadao)
    # Sempre buscar cuidados especiais: se existir registo, o cidadão tem cuidados (independente da flag)
    ce = obter_cuidados_especiais(db, id_cidadao)
    # Base64 pode vir com prefixo data:image/...;base64, — enviar só o payload para o frontend montar o data URL
    fotografia_b64 = getattr(c, "fotografia_base64", None) or None
    if fotografia_b64 and isinstance(fotografia_b64, str) and fotografia_b64.startswith("data:"):
        fotografia_b64 = fotografia_b64.split(",", 1)[-1] if "," in fotografia_b64 else None
    return CidadaoParaAutoridadeResponse(
        id=c.id,
        nome=c.nome,
        data_nascimento=c.data_nascimento,
        telefone=c.telefone,
        bi=c.bi,
        email=c.email,
        fotografia_url=c.fotografia_url,
        fotografia_base64=fotografia_b64,
        genero=c.genero,
        precisa_cuidados_especiais=ce is not None or getattr(c, "precisa_cuidados_especiais", False),
        ativo=getattr(c, "ativo", None),
        created_at=c.created_at,
        contatos_emergencia=[ContatoEmergenciaResponse.model_validate(x) for x in contatos],
        cuidados_especiais=CuidadosEspeciaisResponse.model_validate(ce) if ce else None,
    )


@router.get("/{alerta_id}/midias", response_model=list[MidiaOcorrenciaResponse])
def listar_midias_alerta_endpoint(
    alerta_id: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    """Autoridade: lista as mídias do alerta (ex.: vídeo do relatório da ocorrência). Para ver o vídeo: GET {BASE_URL}/api/v1/uploads/{url_path}."""
    alerta = obter_alerta(db, alerta_id)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    midias = listar_midias_alerta(db, alerta_id)
    return [MidiaOcorrenciaResponse.model_validate(m) for m in midias]


@router.get("/{alerta_id}", response_model=AlertaResponse)
def obter_alerta_endpoint(
    alerta_id: int,
    db=Depends(get_db),
    _payload=Depends(require_autoridade),
):
    alerta = obter_alerta(db, alerta_id)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    return AlertaResponse.model_validate(alerta)


@router.patch("/{alerta_id}/atribuir", response_model=AlertaResponse)
def atribuir_autoridade_endpoint(
  alerta_id: int,
  body: AlertaAtribuirAutoridade,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    alerta = atribuir_autoridade(db, alerta_id, body.id_autoridade)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    return AlertaResponse.model_validate(alerta)


@router.patch("/{alerta_id}/estado", response_model=AlertaResponse)
async def atualizar_estado_endpoint(
  alerta_id: int,
  body: AlertaEstadoUpdate,
  db=Depends(get_db),
  _payload=Depends(require_autoridade),
):
    alerta = atualizar_estado(db, alerta_id, body.estado, motivo=body.motivo)
    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado.")
    if alerta.id_cidadao and body.estado in ("cancelado", "resolvido"):
        situacao = "concluida" if body.estado == "resolvido" else "cancelada"
        motivo = body.motivo or getattr(alerta, "motivo_cancelamento", None)
        _notificar_contatos_ocorrencia_encerrada(db, alerta.id_cidadao, situacao, motivo)
    if body.estado in ("cancelado", "resolvido"):
        await ws_manager.broadcast_alertas({
            "evento": "alerta_encerrado",
            "alerta_id": alerta_id,
        })
    return AlertaResponse.model_validate(alerta)
