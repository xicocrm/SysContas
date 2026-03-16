from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import Empresa, Escritorio, ModuloPermissao, User
from app.schemas import EmpresaCreate, EmpresaRead, EscritorioCreate, EscritorioRead

router = APIRouter(prefix="/empresas", tags=["Empresas"])


@router.post("", response_model=EmpresaRead)
def create_empresa(payload: EmpresaCreate, session: Session = Depends(get_session)) -> EmpresaRead:
    empresa = Empresa(nome=payload.nome, cnpj=payload.cnpj)
    session.add(empresa)
    session.commit()
    session.refresh(empresa)
    return empresa


@router.get("", response_model=list[EmpresaRead])
def list_empresas(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[EmpresaRead]:
    if current_user.is_superuser:
        return list(session.exec(select(Empresa)).all())

    empresa = session.exec(select(Empresa).where(Empresa.id == current_user.empresa_id)).first()
    return [empresa] if empresa else []


@router.post(
    "/escritorios",
    response_model=EscritorioRead,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CADASTROS))],
)
def create_escritorio(
    payload: EscritorioCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EscritorioRead:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Você não pode criar para outra empresa.")

    escritorio = Escritorio(**payload.model_dump())
    session.add(escritorio)
    session.commit()
    session.refresh(escritorio)
    return escritorio


@router.get(
    "/{empresa_id}/escritorios",
    response_model=list[EscritorioRead],
    dependencies=[Depends(require_module_permission(ModuloPermissao.CADASTROS))],
)
def list_escritorios(
    empresa_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[EscritorioRead]:
    if not current_user.is_superuser and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Você não pode consultar outra empresa.")

    return list(session.exec(select(Escritorio).where(Escritorio.empresa_id == empresa_id)).all())
