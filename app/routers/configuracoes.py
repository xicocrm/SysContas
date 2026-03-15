from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import ModuloPermissao, User
from app.schemas import UserPermissionsUpdate, UserRead

router = APIRouter(prefix="/configuracoes", tags=["Configurações"])


def _to_user_read(user: User) -> UserRead:
    perms = [p for p in user.permissoes_csv.split(",") if p]
    return UserRead(
        id=user.id,
        empresa_id=user.empresa_id,
        nome=user.nome,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        permissoes=perms,  # type: ignore[arg-type]
    )


@router.patch(
    "/usuarios/{user_id}/permissoes",
    response_model=UserRead,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def atualizar_permissoes_usuario(
    user_id: int,
    payload: UserPermissionsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Apenas superusuário pode alterar permissões.")

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    user.permissoes_csv = ",".join(sorted({p.value for p in payload.permissoes}))
    if payload.is_active is not None:
        user.is_active = payload.is_active

    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_user_read(user)
