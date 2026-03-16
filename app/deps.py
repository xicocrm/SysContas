from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db import get_session
from app.models import ModuloPermissao, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _parse_permissions(permissoes_csv: str) -> set[str]:
    if not permissoes_csv.strip():
        return set()
    return {item.strip() for item in permissoes_csv.split(",") if item.strip()}


def get_current_user(
    session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject: str | None = payload.get("sub")
        if not subject or not subject.startswith("user:"):
            raise credentials_exception
        user_id = int(subject.split(":", maxsplit=1)[1])
    except (JWTError, ValueError):
        raise credentials_exception

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_module_permission(module: ModuloPermissao) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        allowed = _parse_permissions(current_user.permissoes_csv)
        if module.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sem permissão para módulo: {module.value}",
            )
        return current_user

    return dependency


def ensure_same_empresa(current_user: User, empresa_id: int) -> None:
    if current_user.is_superuser:
        return
    if current_user.empresa_id != empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode operar dados da sua empresa.",
        )
