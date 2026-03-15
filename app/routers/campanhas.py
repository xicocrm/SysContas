from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import Campanha, ModuloPermissao, User
from app.schemas import CampanhaInput

router = APIRouter(prefix="/campanhas", tags=["Campanhas"])


@router.post(
    "",
    response_model=Campanha,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CAMPANHAS))],
)
def create_campanha(
    payload: CampanhaInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Campanha:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")
    item = Campanha(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
