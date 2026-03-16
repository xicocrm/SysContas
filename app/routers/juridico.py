from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import ModuloPermissao, Processo, Protocolo, User
from app.schemas import ProcessoInput, ProtocoloInput

router = APIRouter(prefix="/juridico", tags=["Jurídico"])


@router.post(
    "/processos",
    response_model=Processo,
    dependencies=[Depends(require_module_permission(ModuloPermissao.PROCESSOS))],
)
def create_processo(
    payload: ProcessoInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Processo:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = Processo(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post(
    "/protocolos",
    response_model=Protocolo,
    dependencies=[Depends(require_module_permission(ModuloPermissao.PROTOCOLOS))],
)
def create_protocolo(
    payload: ProtocoloInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Protocolo:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = Protocolo(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
