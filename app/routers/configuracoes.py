from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_current_database_url, get_session, reconfigure_database
from app.deps import get_current_user, require_module_permission
from app.models import IntegracaoBancoDados, ModuloPermissao, TipoBancoDados, User
from app.schemas import (
    DatabaseConnectionTestResult,
    DatabaseIntegrationApplyInput,
    DatabaseIntegrationCreate,
    DatabaseIntegrationRead,
    UserPermissionsUpdate,
    UserRead,
)
from app.services.database_integrations import (
    build_database_url,
    mask_database_url,
    persist_database_url_in_env,
    test_database_connection,
)

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


def _to_database_read(item: IntegracaoBancoDados) -> DatabaseIntegrationRead:
    return DatabaseIntegrationRead(
        id=item.id,
        empresa_id=item.empresa_id,
        nome=item.nome,
        tipo=item.tipo,
        database_url_mascarada=mask_database_url(item.database_url),
        ativo=item.ativo,
        principal=item.principal,
        created_at=item.created_at,
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


@router.get(
    "/bancos-dados/tipos",
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def listar_tipos_bancos_dados():
    return {"tipos": [item.value for item in TipoBancoDados]}


@router.post(
    "/bancos-dados",
    response_model=DatabaseIntegrationRead,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def salvar_integracao_banco_dados(
    payload: DatabaseIntegrationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DatabaseIntegrationRead:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    database_url = payload.database_url
    if not database_url:
        try:
            database_url = build_database_url(
                tipo=payload.tipo,
                host=payload.host,
                porta=payload.porta,
                database_name=payload.database_name,
                username=payload.username,
                password=payload.password,
                sqlite_path=payload.sqlite_path,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    ok, message = test_database_connection(database_url)
    if not ok:
        raise HTTPException(status_code=400, detail=message)

    existing = session.exec(
        select(IntegracaoBancoDados).where(
            IntegracaoBancoDados.empresa_id == payload.empresa_id,
            IntegracaoBancoDados.nome == payload.nome,
        )
    ).first()

    if payload.principal:
        current_principals = session.exec(
            select(IntegracaoBancoDados).where(
                IntegracaoBancoDados.empresa_id == payload.empresa_id,
                IntegracaoBancoDados.principal.is_(True),
            )
        ).all()
        for principal in current_principals:
            principal.principal = False
            session.add(principal)

    if existing:
        existing.tipo = payload.tipo
        existing.database_url = database_url
        existing.ativo = True
        existing.principal = payload.principal
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return _to_database_read(existing)

    item = IntegracaoBancoDados(
        empresa_id=payload.empresa_id,
        nome=payload.nome,
        tipo=payload.tipo,
        database_url=database_url,
        ativo=True,
        principal=payload.principal,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return _to_database_read(item)


@router.get(
    "/{empresa_id}/bancos-dados",
    response_model=list[DatabaseIntegrationRead],
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def listar_integracoes_bancos_dados(
    empresa_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[DatabaseIntegrationRead]:
    if not current_user.is_superuser and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    items = session.exec(
        select(IntegracaoBancoDados).where(IntegracaoBancoDados.empresa_id == empresa_id)
    ).all()
    return [_to_database_read(item) for item in items]


@router.post(
    "/bancos-dados/{integracao_id}/testar",
    response_model=DatabaseConnectionTestResult,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def testar_integracao_banco_dados(
    integracao_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DatabaseConnectionTestResult:
    item = session.exec(select(IntegracaoBancoDados).where(IntegracaoBancoDados.id == integracao_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Integração não encontrada.")
    if not current_user.is_superuser and current_user.empresa_id != item.empresa_id:
        raise HTTPException(status_code=403, detail="Empresa inválida.")

    ok, message = test_database_connection(item.database_url)
    return DatabaseConnectionTestResult(ok=ok, message=message)


@router.post(
    "/bancos-dados/{integracao_id}/aplicar-armazenamento",
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def aplicar_banco_para_armazenamento(
    integracao_id: int,
    payload: DatabaseIntegrationApplyInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Apenas superusuário pode trocar o banco ativo de armazenamento.",
        )

    item = session.exec(select(IntegracaoBancoDados).where(IntegracaoBancoDados.id == integracao_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Integração não encontrada.")

    ok, message = test_database_connection(item.database_url)
    if not ok:
        raise HTTPException(status_code=400, detail=message)

    # Garante apenas um banco principal por empresa antes de aplicar.
    principals = session.exec(
        select(IntegracaoBancoDados).where(
            IntegracaoBancoDados.empresa_id == item.empresa_id,
            IntegracaoBancoDados.principal.is_(True),
        )
    ).all()
    for current in principals:
        current.principal = False
        session.add(current)

    item.principal = True
    item.ativo = True
    session.add(item)
    session.commit()

    reconfigure_database(item.database_url)

    if payload.persistir_em_arquivo:
        persist_database_url_in_env(item.database_url)

    return {
        "message": "Banco de dados aplicado como armazenamento da aplicação.",
        "empresa_id": item.empresa_id,
        "integracao_id": item.id,
        "database_url_mascarada": mask_database_url(item.database_url),
        "persistido_em_arquivo": payload.persistir_em_arquivo,
    }


@router.get(
    "/armazenamento-ativo",
    dependencies=[Depends(require_module_permission(ModuloPermissao.CONFIGURACOES))],
)
def armazenamento_ativo(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Apenas superusuário pode visualizar armazenamento ativo.")
    return {"database_url_mascarada": mask_database_url(get_current_database_url())}
