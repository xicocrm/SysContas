from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import ContaPagar, ContaReceber, ModuloPermissao, User
from app.schemas import ContaInput

router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


@router.post(
    "/contas-pagar",
    response_model=ContaPagar,
    dependencies=[Depends(require_module_permission(ModuloPermissao.FINANCEIRO))],
)
def create_conta_pagar(
    payload: ContaInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ContaPagar:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = ContaPagar(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post(
    "/contas-receber",
    response_model=ContaReceber,
    dependencies=[Depends(require_module_permission(ModuloPermissao.FINANCEIRO))],
)
def create_conta_receber(
    payload: ContaInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ContaReceber:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = ContaReceber(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get(
    "/{empresa_id}/resumo",
    dependencies=[Depends(require_module_permission(ModuloPermissao.FINANCEIRO))],
)
def resumo_financeiro(
    empresa_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    pagar = list(session.exec(select(ContaPagar).where(ContaPagar.empresa_id == empresa_id)).all())
    receber = list(
        session.exec(select(ContaReceber).where(ContaReceber.empresa_id == empresa_id)).all()
    )
    total_pagar = sum(item.valor for item in pagar if not item.pago)
    total_receber = sum(item.valor for item in receber if not item.recebido)
    return {
        "empresa_id": empresa_id,
        "total_a_pagar": total_pagar,
        "total_a_receber": total_receber,
        "saldo_previsto": total_receber - total_pagar,
    }
