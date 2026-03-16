from datetime import date, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import (
    BancoIntegracao,
    CanalIntegracao,
    ModuloPermissao,
    TipoBancoDados,
    TipoDocumento,
)

T = TypeVar("T")


def only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Message(BaseModel):
    message: str


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int


class EmpresaCreate(BaseModel):
    nome: str
    cnpj: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        digits = only_digits(value)
        if len(digits) != 14:
            raise ValueError("CNPJ precisa ter 14 dígitos.")
        return digits


class EmpresaRead(BaseModel):
    id: int
    nome: str
    cnpj: Optional[str]
    ativa: bool
    created_at: datetime


class EscritorioCreate(BaseModel):
    empresa_id: int
    nome: str
    cnpj: Optional[str] = None
    cep: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class EscritorioRead(BaseModel):
    id: int
    empresa_id: int
    nome: str
    cnpj: Optional[str]
    cep: Optional[str]
    endereco: Optional[str]
    cidade: Optional[str]
    estado: Optional[str]
    created_at: datetime


class UserCreate(BaseModel):
    empresa_id: int
    nome: str
    email: EmailStr
    password: str = Field(min_length=8)
    is_superuser: bool = False
    permissoes: list[ModuloPermissao] = []


class UserRead(BaseModel):
    id: int
    empresa_id: int
    nome: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    permissoes: list[ModuloPermissao]


class UserPermissionsUpdate(BaseModel):
    permissoes: list[ModuloPermissao]
    is_active: Optional[bool] = None


class DatabaseIntegrationCreate(BaseModel):
    empresa_id: int
    nome: str
    tipo: TipoBancoDados
    database_url: Optional[str] = None
    host: Optional[str] = None
    porta: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sqlite_path: Optional[str] = None
    principal: bool = False


class DatabaseIntegrationRead(BaseModel):
    id: int
    empresa_id: int
    nome: str
    tipo: TipoBancoDados
    database_url_mascarada: str
    ativo: bool
    principal: bool
    created_at: datetime


class DatabaseConnectionTestResult(BaseModel):
    ok: bool
    message: str


class DatabaseIntegrationApplyInput(BaseModel):
    persistir_em_arquivo: bool = False


class ClienteCreate(BaseModel):
    empresa_id: int
    tipo_documento: TipoDocumento
    documento: str
    nome_razao: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    senha_portal: Optional[str] = Field(default=None, min_length=8)

    @field_validator("documento")
    @classmethod
    def validate_documento(cls, value: str) -> str:
        digits = only_digits(value)
        if len(digits) not in (11, 14):
            raise ValueError("Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")
        return digits

    @field_validator("cep")
    @classmethod
    def normalize_cep(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        digits = only_digits(value)
        if len(digits) != 8:
            raise ValueError("CEP deve ter 8 dígitos.")
        return digits


class ClienteRead(BaseModel):
    id: int
    empresa_id: int
    tipo_documento: TipoDocumento
    documento: str
    nome_razao: str
    email: Optional[EmailStr]
    telefone: Optional[str]
    cep: Optional[str]
    endereco: Optional[str]
    numero: Optional[str]
    bairro: Optional[str]
    cidade: Optional[str]
    estado: Optional[str]
    portal_bloqueado: bool
    created_at: datetime


class ClientePortalBlockUpdate(BaseModel):
    bloqueado: bool


class PortalLoginInput(BaseModel):
    empresa_id: int
    documento: str
    senha: str


class ContaInput(BaseModel):
    empresa_id: int
    cliente_id: Optional[int] = None
    descricao: str
    valor: float = Field(gt=0)
    vencimento: date


class NegociacaoInput(BaseModel):
    empresa_id: int
    cliente_id: int
    titulo: str
    etapa: str
    valor_estimado: Optional[float] = Field(default=None, ge=0)


class PropostaInput(BaseModel):
    empresa_id: int
    cliente_id: int
    titulo: str
    descricao: Optional[str] = None
    valor: float = Field(gt=0)


class ContratoInput(BaseModel):
    empresa_id: int
    cliente_id: int
    numero: str
    objeto: str
    inicio: date
    fim: Optional[date] = None


class ProcessoInput(BaseModel):
    empresa_id: int
    cliente_id: int
    numero_processo: str
    tribunal: Optional[str] = None
    assunto: str


class ProtocoloInput(BaseModel):
    empresa_id: int
    cliente_id: Optional[int] = None
    codigo: str
    descricao: str
    data_evento: date


class CampanhaInput(BaseModel):
    empresa_id: int
    nome: str
    canal: str
    publico_alvo: Optional[str] = None


class IntegracaoCanalInput(BaseModel):
    empresa_id: int
    provedor: CanalIntegracao
    credenciais_json: str


class IntegracaoBancoInput(BaseModel):
    empresa_id: int
    banco: BancoIntegracao
    credenciais_json: str


class NotificationInput(BaseModel):
    empresa_id: int
    cliente_id: int
    assunto: str
    mensagem: str
    enviar_email: bool = True
    enviar_whatsapp: bool = False
