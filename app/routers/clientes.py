from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.security import get_password_hash
from app.db import get_session
from app.deps import get_current_user, require_module_permission
from app.models import Cliente, ModuloPermissao, TipoDocumento, User
from app.schemas import ClienteCreate, ClientePortalBlockUpdate, ClienteRead
from app.services.external_lookup import lookup_cep, lookup_cnpj_receita

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("/lookup/cnpj/{cnpj}")
async def cnpj_lookup(cnpj: str):
    try:
        return await lookup_cnpj_receita(cnpj)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao consultar CNPJ: {exc}")


@router.get("/lookup/cep/{cep}")
async def cep_lookup(cep: str):
    try:
        return await lookup_cep(cep)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao consultar CEP: {exc}")


@router.post(
    "",
    response_model=ClienteRead,
    dependencies=[Depends(require_module_permission(ModuloPermissao.CADASTROS))],
)
async def create_cliente(
    payload: ClienteCreate,
    auto_fill_endereco: bool = Query(default=True),
    auto_fill_cnpj: bool = Query(default=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ClienteRead:
    if not current_user.is_superuser and current_user.empresa_id != payload.empresa_id:
        raise HTTPException(status_code=403, detail="Você não pode criar cliente de outra empresa.")

    if payload.tipo_documento == TipoDocumento.CPF and len(payload.documento) != 11:
        raise HTTPException(status_code=400, detail="CPF inválido.")
    if payload.tipo_documento == TipoDocumento.CNPJ and len(payload.documento) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido.")

    existing = session.exec(
        select(Cliente).where(
            Cliente.empresa_id == payload.empresa_id, Cliente.documento == payload.documento
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cliente já cadastrado com este documento.")

    data = payload.model_dump(exclude={"senha_portal"})

    if payload.tipo_documento == TipoDocumento.CNPJ and auto_fill_cnpj:
        try:
            cnpj_data = await lookup_cnpj_receita(payload.documento)
            data["nome_razao"] = payload.nome_razao or cnpj_data.get("razao_social") or payload.nome_razao
            data["email"] = payload.email or cnpj_data.get("email")
            data["telefone"] = payload.telefone or cnpj_data.get("telefone")
            data["cep"] = payload.cep or cnpj_data.get("cep")
            data["endereco"] = payload.endereco or cnpj_data.get("logradouro")
            data["numero"] = payload.numero or cnpj_data.get("numero")
            data["bairro"] = payload.bairro or cnpj_data.get("bairro")
            data["cidade"] = payload.cidade or cnpj_data.get("cidade")
            data["estado"] = payload.estado or cnpj_data.get("estado")
        except Exception:
            pass

    if data.get("cep") and auto_fill_endereco and not data.get("endereco"):
        try:
            cep_data = await lookup_cep(data["cep"])
            data["endereco"] = cep_data.get("logradouro")
            data["bairro"] = cep_data.get("bairro")
            data["cidade"] = cep_data.get("cidade")
            data["estado"] = cep_data.get("estado")
        except Exception:
            pass

    cliente = Cliente(**data)
    if payload.senha_portal:
        cliente.portal_senha_hash = get_password_hash(payload.senha_portal)

    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


@router.get(
    "/{empresa_id}",
    response_model=list[ClienteRead],
    dependencies=[Depends(require_module_permission(ModuloPermissao.CADASTROS))],
)
def list_clientes(
    empresa_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ClienteRead]:
    if not current_user.is_superuser and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Você não pode consultar outra empresa.")
    return list(session.exec(select(Cliente).where(Cliente.empresa_id == empresa_id)).all())


@router.patch(
    "/{cliente_id}/portal",
    response_model=ClienteRead,
    dependencies=[Depends(require_module_permission(ModuloPermissao.PORTAL_CLIENTE))],
)
def block_unblock_portal(
    cliente_id: int,
    payload: ClientePortalBlockUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ClienteRead:
    cliente = session.exec(select(Cliente).where(Cliente.id == cliente_id)).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    if not current_user.is_superuser and current_user.empresa_id != cliente.empresa_id:
        raise HTTPException(status_code=403, detail="Você não pode alterar outra empresa.")

    cliente.portal_bloqueado = payload.bloqueado
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente
