from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import Contrato, ModuloPermissao, Negociacao, Proposta, User
from app.schemas import ContratoInput, NegociacaoInput, PropostaInput

router = APIRouter(prefix="/comercial", tags=["Comercial"])


@router.post(
    "/negociacoes",
    response_model=Negociacao,
    dependencies=[Depends(require_module_permission(ModuloPermissao.NEGOCIACOES))],
)
def create_negociacao(
    payload: NegociacaoInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Negociacao:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = Negociacao(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post(
    "/propostas",
    response_model=Proposta,
    dependencies=[Depends(require_module_permission(ModuloPermissao.PROPOSTAS))],
)
def create_proposta(
    payload: PropostaInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Proposta:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = Proposta(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post(
    "/contratos",
    response_model=Contrato,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONTRATOS))],
)
def create_contrato(
    payload: ContratoInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Contrato:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = Contrato(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
