from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db import engine
from app.models import Empresa, User


def ensure_seed_admin() -> dict[str, str]:
    if not settings.auto_seed_admin:
        return {"status": "skipped", "message": "auto_seed_admin desativado"}

    email = (settings.seed_admin_email or "").strip().lower()
    password = settings.seed_admin_password or ""
    if not email or not password:
        return {"status": "skipped", "message": "seed_admin_email/senha ausentes"}

    with Session(engine) as session:
        company = None
        cnpj = (settings.seed_company_cnpj or "").strip()
        if cnpj:
            company = session.exec(select(Empresa).where(Empresa.cnpj == cnpj)).first()
        if not company:
            company = session.exec(select(Empresa).where(Empresa.nome == settings.seed_company_name)).first()
        if not company:
            company = Empresa(nome=settings.seed_company_name, cnpj=cnpj or None, ativa=True)
            session.add(company)
            session.commit()
            session.refresh(company)

        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            user.empresa_id = company.id
            user.is_active = True
            user.is_superuser = True
            if settings.seed_admin_update_password:
                user.hashed_password = get_password_hash(password)
            session.add(user)
            session.commit()
            return {"status": "updated", "message": f"admin pronto: {email}"}

        user = User(
            empresa_id=company.id,
            nome=settings.seed_admin_name,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
            permissoes_csv="",
        )
        session.add(user)
        session.commit()
        return {"status": "created", "message": f"admin criado: {email}"}
