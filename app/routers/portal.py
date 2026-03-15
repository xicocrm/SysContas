from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token, verify_password
from app.db import get_session
from app.models import Cliente, ContaReceber
from app.schemas import PortalLoginInput, Token
from app.services.external_lookup import normalize_digits

router = APIRouter(prefix="/portal", tags=["Portal do Cliente"])
oauth2_portal = OAuth2PasswordBearer(tokenUrl="/portal/login")


@router.post("/login", response_model=Token)
def portal_login(payload: PortalLoginInput, session: Session = Depends(get_session)) -> Token:
    documento = normalize_digits(payload.documento)
    cliente = session.exec(
        select(Cliente).where(
            Cliente.empresa_id == payload.empresa_id, Cliente.documento == documento
        )
    ).first()
    if not cliente or not cliente.portal_senha_hash:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")
    if cliente.portal_bloqueado:
        raise HTTPException(status_code=403, detail="Portal do cliente bloqueado.")
    if not verify_password(payload.senha, cliente.portal_senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    return Token(access_token=create_access_token(f"cliente:{cliente.id}"))


def get_current_cliente_portal(
    token: str = Depends(oauth2_portal), session: Session = Depends(get_session)
) -> Cliente:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado no portal.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject: str | None = payload.get("sub")
        if not subject or not subject.startswith("cliente:"):
            raise credentials_exception
        cliente_id = int(subject.split(":", maxsplit=1)[1])
    except (JWTError, ValueError):
        raise credentials_exception

    cliente = session.exec(select(Cliente).where(Cliente.id == cliente_id)).first()
    if not cliente or cliente.portal_bloqueado:
        raise credentials_exception
    return cliente


@router.get("/me")
def portal_me(cliente: Cliente = Depends(get_current_cliente_portal)):
    return cliente


@router.get("/me/contas-receber")
def portal_contas_receber(
    cliente: Cliente = Depends(get_current_cliente_portal),
    session: Session = Depends(get_session),
):
    contas = list(
        session.exec(
            select(ContaReceber).where(
                ContaReceber.empresa_id == cliente.empresa_id, ContaReceber.cliente_id == cliente.id
            )
        ).all()
    )
    return {"cliente_id": cliente.id, "contas": contas}
