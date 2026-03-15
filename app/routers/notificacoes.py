from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import CanalIntegracao, Cliente, IntegracaoCanal, ModuloPermissao, User
from app.schemas import NotificationInput
from app.services.notifications import dispatch_notification

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.post(
    "/enviar",
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def enviar_notificacao(
    payload: NotificationInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    cliente = session.exec(
        select(Cliente).where(
            Cliente.id == payload.cliente_id,
            Cliente.empresa_id == payload.empresa_id,
        )
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    whatsapp_integration = session.exec(
        select(IntegracaoCanal).where(
            IntegracaoCanal.empresa_id == payload.empresa_id,
            IntegracaoCanal.provedor.in_(
                [
                    CanalIntegracao.WHATSAPP,
                    CanalIntegracao.WAVOIP,
                    CanalIntegracao.A_API,
                    CanalIntegracao.FALE_PACO,
                    CanalIntegracao.WLATICKET,
                ]
            ),
            IntegracaoCanal.ativo.is_(True),
        )
    ).first()

    return dispatch_notification(
        assunto=payload.assunto,
        mensagem=payload.mensagem,
        email=cliente.email,
        telefone=cliente.telefone,
        send_email=payload.enviar_email,
        send_whatsapp=payload.enviar_whatsapp,
        whatsapp_integration=whatsapp_integration,
    )
