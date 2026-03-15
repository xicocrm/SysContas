from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db import create_db_and_tables, get_session
from app.deps import get_current_user
from app.models import Empresa, User
from app.schemas import Message, Token, UserCreate, UserRead
from app.services.bootstrap_admin import ensure_seed_admin

router = APIRouter(prefix="/auth", tags=["Auth"])


def _permissions_to_csv(permissoes: list) -> str:
    return ",".join(sorted({p.value for p in permissoes}))


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


@router.post("/bootstrap", response_model=Message)
def bootstrap_first_user(payload: UserCreate, session: Session = Depends(get_session)) -> Message:
    existing = session.exec(select(User)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bootstrap já executado.")
    empresa = session.exec(select(Empresa).where(Empresa.id == payload.empresa_id)).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    user = User(
        empresa_id=payload.empresa_id,
        nome=payload.nome,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_superuser=True,
        permissoes_csv="",
    )
    session.add(user)
    session.commit()
    return Message(message="Usuário administrador inicial criado.")


@router.post("/users", response_model=UserRead)
def create_user(
    payload: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Apenas administrador pode criar usuários.")
    empresa = session.exec(select(Empresa).where(Empresa.id == payload.empresa_id)).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    exists = session.exec(select(User).where(User.email == payload.email)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    user = User(
        empresa_id=payload.empresa_id,
        nome=payload.nome,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_superuser=payload.is_superuser,
        permissoes_csv=_permissions_to_csv(payload.permissoes),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_user_read(user)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> Token:
    try:
        user = session.exec(select(User).where(User.email == form_data.username)).first()
    except SQLAlchemyError:
        session.rollback()
        # Self-heal path: recreate schema and seed admin if DB is inconsistent.
        create_db_and_tables()
        ensure_seed_admin()
        try:
            user = session.exec(select(User).where(User.email == form_data.username)).first()
        except SQLAlchemyError:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Banco indisponível temporariamente. Tente novamente em instantes.",
            )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")

    token = create_access_token(f"user:{user.id}")
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return _to_user_read(current_user)
