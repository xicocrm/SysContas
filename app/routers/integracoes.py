from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import (
    BancoIntegracao,
    CanalIntegracao,
    IntegracaoBanco,
    IntegracaoCanal,
    ModuloPermissao,
    User,
)
from app.schemas import IntegracaoBancoInput, IntegracaoCanalInput

router = APIRouter(prefix="/integracoes", tags=["Integrações"])


@router.get("/provedores")
def provedores():
    return {
        "canais": [item.value for item in CanalIntegracao],
        "bancos": [item.value for item in BancoIntegracao],
    }


@router.post(
    "/canais",
    response_model=IntegracaoCanal,
    dependencies=[Depends(require_module_permission(ModuloPermissao.INTEGRACOES))],
)
def salvar_integracao_canal(
    payload: IntegracaoCanalInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IntegracaoCanal:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    existing = session.exec(
        select(IntegracaoCanal).where(
            IntegracaoCanal.empresa_id == payload.empresa_id,
            IntegracaoCanal.provedor == payload.provedor,
        )
    ).first()

    if existing:
        existing.credenciais_json = payload.credenciais_json
        existing.ativo = True
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    item = IntegracaoCanal(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post(
    "/bancos",
    response_model=IntegracaoBanco,
    dependencies=[Depends(require_module_permission(ModuloPermissao.INTEGRACOES))],
)
def salvar_integracao_banco(
    payload: IntegracaoBancoInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IntegracaoBanco:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    existing = session.exec(
        select(IntegracaoBanco).where(
            IntegracaoBanco.empresa_id == payload.empresa_id,
            IntegracaoBanco.banco == payload.banco,
        )
    ).first()

    if existing:
        existing.credenciais_json = payload.credenciais_json
        existing.ativo = True
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    item = IntegracaoBanco(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get(
    "/{empresa_id}",
    dependencies=[Depends(require_module_permission(ModuloPermissao.INTEGRACOES))],
)
def listar_integracoes(
    empresa_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    canais = list(session.exec(select(IntegracaoCanal).where(IntegracaoCanal.empresa_id == empresa_id)))
    bancos = list(session.exec(select(IntegracaoBanco).where(IntegracaoBanco.empresa_id == empresa_id)))
    return {"empresa_id": empresa_id, "canais": canais, "bancos": bancos}
