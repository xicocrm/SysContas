from app.models import IntegracaoCanal


def dispatch_notification(
    assunto: str,
    mensagem: str,
    email: str | None,
    telefone: str | None,
    send_email: bool,
    send_whatsapp: bool,
    whatsapp_integration: IntegracaoCanal | None = None,
) -> dict:
    """
    Serviço de notificação (MVP):
    - Email: placeholder para integração SMTP/provider.
    - WhatsApp: placeholder baseado no provedor ativo configurado.
    """
    eventos: list[str] = []

    if send_email and email:
        eventos.append(f"email queued to {email}: {assunto}")
    elif send_email:
        eventos.append("email skipped (cliente sem email)")

    if send_whatsapp and telefone:
        if whatsapp_integration:
            eventos.append(
                f"whatsapp queued via {whatsapp_integration.provedor.value} to {telefone}"
            )
        else:
            eventos.append("whatsapp skipped (sem integração ativa)")
    elif send_whatsapp:
        eventos.append("whatsapp skipped (cliente sem telefone)")

    return {"assunto": assunto, "mensagem": mensagem, "eventos": eventos}
