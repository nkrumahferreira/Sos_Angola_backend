"""
Envio de mensagens WhatsApp via QuePasa (https://github.com/nocodeleaks/quepasa).
Usado para notificar o cuidador: horários de medicação e alerta quando o utilizador ignora 3 doses.
"""
import re
import httpx
from app.config import settings

# Código de país Angola (para normalizar número)
DEFAULT_COUNTRY_CODE = "244"


def _normalize_phone_to_chat_id(telefone: str) -> str:
    """Converte telefone para formato WhatsApp JID (chatid). Ex: 912 345 678 -> 244912345678@s.whatsapp.net"""
    if not telefone or not isinstance(telefone, str):
        return ""
    digits = re.sub(r"\D", "", telefone.strip())
    if not digits:
        return ""
    if not digits.startswith("244"):
        digits = DEFAULT_COUNTRY_CODE + digits.lstrip("0")
    return f"{digits}@s.whatsapp.net"


def enviar_whatsapp(telefone: str, texto: str) -> bool:
    """
    Envia mensagem de texto via QuePasa para o número indicado.
    Retorna True se enviado com sucesso, False caso contrário (config ausente, erro HTTP, etc.).
    """
    if not settings.QUEPASA_BASE_URL or not settings.QUEPASA_TOKEN:
        return False
    chat_id = _normalize_phone_to_chat_id(telefone)
    if not chat_id:
        return False
    url = settings.QUEPASA_BASE_URL.rstrip("/") + "/send"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-QUEPASA-TOKEN": settings.QUEPASA_TOKEN,
        "X-QUEPASA-CHATID": chat_id,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json={"text": texto}, headers=headers)
            return 200 <= r.status_code < 300
    except Exception:
        return False


def _get_attr(m, attr: str, default=None):
    if hasattr(m, attr):
        return getattr(m, attr)
    if isinstance(m, dict):
        return m.get(attr, default)
    return default


def _formatar_data_hora(proxima_dose) -> str:
    """Formata proxima_dose (datetime ou str) para exibição legível."""
    if not proxima_dose:
        return ""
    try:
        from datetime import datetime
        if isinstance(proxima_dose, str):
            dt = datetime.fromisoformat(proxima_dose.replace("Z", "+00:00"))
        else:
            dt = proxima_dose
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(proxima_dose)


def _formatar_dias_semana(ds) -> str:
    """Formata dias_semana (lista ou string JSON) para texto legível."""
    if not ds:
        return ""
    if isinstance(ds, (list, tuple)):
        return ", ".join(str(d).strip() for d in ds)
    if isinstance(ds, str) and ds.strip().startswith("["):
        try:
            import json
            arr = json.loads(ds)
            return ", ".join(str(d).strip() for d in arr)
        except Exception:
            pass
    return str(ds)


def formatar_mensagem_horarios_medicacao(
    nome_cidadao: str,
    medicacoes: list,
    nome_contato_emergencia: str | None = None,
) -> str:
    """Gera texto amigável e profissional com os horários de medicação para enviar ao cuidador."""
    nome_contato = (nome_contato_emergencia or "prezado(a)").strip()
    paciente = nome_cidadao or "o paciente"
    if not medicacoes:
        return (
            "Olá, *{nome}*! 👋\n\n"
            "Daqui fala o *SOS Angola*. "
            "Informamos que não há medicamentos registados no momento para *{paciente}*.\n\n"
            "_Mensagem automática – SOS Angola_"
        ).format(nome=nome_contato, paciente=paciente)
    linhas = [
        "Olá, *{nome}*! 👋".format(nome=nome_contato),
        "",
        "Daqui fala o *SOS Angola*. "
        "Era para avisar que chegou a hora de *{paciente}* cumprir a medicação. "
        "Segue o resumo dos medicamentos e horários:".format(paciente=paciente),
        "",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for i, m in enumerate(medicacoes, 1):
        nome = _get_attr(m, "nome_medicamento") or "Medicamento"
        dose_val = _get_attr(m, "dose_valor")
        dose_uni = _get_attr(m, "dose_unidade")
        dose_txt = ""
        if dose_val is not None and dose_uni:
            dose_txt = f"{dose_val} {dose_uni}".strip()
        elif _get_attr(m, "dosagem"):
            dose_txt = _get_attr(m, "dosagem") or ""

        # Descrição da frequência
        freq_txt = ""
        tipo_freq = _get_attr(m, "tipo_frequencia")
        if tipo_freq == "intervalo":
            ih = _get_attr(m, "intervalo_horas")
            if ih is not None:
                freq_txt = f"De {ih} em {ih} horas"
        elif tipo_freq == "intervalo_dias":
            idays = _get_attr(m, "intervalo_dias")
            hf = _get_attr(m, "horario_fixo")
            if idays is not None:
                freq_txt = f"A cada {idays} dia(s)"
                if hf:
                    freq_txt += f" às {hf}"
        elif tipo_freq == "dias_semana":
            ds = _get_attr(m, "dias_semana")
            hf = _get_attr(m, "horario_fixo")
            if ds:
                dias = _formatar_dias_semana(ds)
                freq_txt = f"Dias: {dias}"
                if hf:
                    freq_txt += f" às {hf}"
        if not freq_txt and _get_attr(m, "horario_fixo"):
            freq_txt = f"Horário: {_get_attr(m, 'horario_fixo')}"
        if not freq_txt and _get_attr(m, "horario_tomar"):
            freq_txt = f"Horário: {_get_attr(m, 'horario_tomar')}"
        if not freq_txt and _get_attr(m, "frequencia_monitorizacao"):
            freq_txt = _get_attr(m, "frequencia_monitorizacao")

        proxima = _formatar_data_hora(_get_attr(m, "proxima_dose"))

        linhas.append(f"\n*{i}. {nome}*")
        if dose_txt:
            linhas.append(f"   • Dose: {dose_txt}")
        if freq_txt:
            linhas.append(f"   • Frequência: {freq_txt}")
        if proxima:
            linhas.append(f"   • Próxima dose: {proxima}")
        linhas.append("")

    linhas.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "Agradecíamos que acompanhasse a medicação dele(a) e que lhe lembrasse de marcar *«Tomei»* na nossa aplicação, "
        "para termos um melhor controle do paciente.",
        "",
        "Em caso de dúvida, contacte o médico assistente.",
        "",
        "_Mensagem automática – SOS Angola_",
    ])
    return "\n".join(linhas).strip()


def formatar_mensagem_alerta_3_ignoradas(nome_cidadao: str, nome_medicamento: str) -> str:
    """Gera texto de alerta profissional para o cuidador quando o paciente ignorou 3 doses seguidas."""
    return (
        "⚠️ *SOS Angola – Alerta de medicação*\n\n"
        "Prezado cuidador,\n\n"
        "Informamos que o paciente *{nome}* não registou a toma do medicamento *{med}* em *três horários consecutivos*.\n\n"
        "• As *autoridades de saúde foram notificadas* automaticamente.\n"
        "• Recomendamos que contacte o paciente para confirmar o seu estado e incentivar o cumprimento da medicação.\n"
        "• Se necessário, contacte também as autoridades ou o médico assistente.\n\n"
        "Esta mensagem é enviada automaticamente pela aplicação SOS Angola."
    ).format(nome=nome_cidadao or "sob sua supervisão", med=nome_medicamento or "indicado")


def formatar_mensagem_sos_contatos(
    nome_cidadao: str,
    endereco_aprox: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Mensagem para os contatos de emergência quando o cidadão envia SOS.
    Inclui coordenadas e link do Google Maps para abrir a localização.
    """
    linhas = [
        "🚨 *SOS Angola – Alerta de emergência*",
        "",
        "*{nome}* está em perigo e enviou um pedido de ajuda através da aplicação SOS Angola.".format(
            nome=nome_cidadao or "Um contacto seu"
        ),
        "",
        "As autoridades foram notificadas com a localização.",
    ]
    if endereco_aprox:
        linhas.append(f"Localização aproximada: {endereco_aprox}")
    if latitude is not None and longitude is not None:
        linhas.append(f"Coordenadas: {latitude:.6f}, {longitude:.6f}")
        maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
        linhas.append(f"Abrir no mapa: {maps_url}")
    linhas.extend([
        "",
        "Recomendamos que tente contactar esta pessoa e, se necessário, as autoridades.",
        "",
        "_Mensagem automática – SOS Angola_",
    ])
    return "\n".join(linhas)


def formatar_mensagem_ocorrencia_encerrada(
    nome_cidadao: str,
    situacao: str,
    motivo: str | None = None,
) -> str:
    """Mensagem para os contatos de emergência quando a ocorrência é cancelada ou concluída.
    situacao: 'cancelada' (pelo utilizador ou pela autoridade) ou 'concluida'.
    """
    if situacao == "concluida":
        titulo = "✅ *SOS Angola – Ocorrência concluída*"
        texto = (
            f"A ocorrência de *{nome_cidadao or 'o seu contacto'}* foi *concluída* pelas autoridades.\n\n"
            "O caso foi encerrado. Pode contactar a pessoa para confirmar que está bem."
        )
    else:
        titulo = "ℹ️ *SOS Angola – Ocorrência cancelada*"
        motivo_txt = f"\nMotivo: {motivo}" if motivo else ""
        texto = (
            f"A ocorrência de *{nome_cidadao or 'o seu contacto'}* foi *cancelada*.{motivo_txt}\n\n"
            "Não é necessária qualquer ação da sua parte."
        )
    return (
        f"{titulo}\n\n"
        f"{texto}\n\n"
        "_Mensagem automática – SOS Angola_"
    )
