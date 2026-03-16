from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TipoDocumento(str, Enum):
    CPF = "cpf"
    CNPJ = "cnpj"


class ModuloPermissao(str, Enum):
    CADASTROS = "cadastros"
    FINANCEIRO = "financeiro"
    NEGOCIACOES = "negociacoes"
    PROPOSTAS = "propostas"
    CONTRATOS = "contratos"
    PROCESSOS = "processos"
    PROTOCOLOS = "protocolos"
    CAMPANHAS = "campanhas"
    INTEGRACOES = "integracoes"
    CONFIGURACOES = "configuracoes"
    PORTAL_CLIENTE = "portal_cliente"


class CanalIntegracao(str, Enum):
    WAVOIP = "wavoip"
    A_API = "a-api"
    FALE_PACO = "fale_paco"
    WLATICKET = "wlaticket"
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class BancoIntegracao(str, Enum):
    ASAAS = "asaas"
    INTER = "inter"
    EFI = "efi"
    CORA = "cora"
    MERCADO_PAGO = "mercado_pago"
    PAGBANK = "pagbank"
    BRADESCO = "bradesco"
    ITAU = "itau"
    BRASIL = "banco_do_brasil"
    CAIXA = "caixa"


class TipoBancoDados(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    SQLSERVER = "sqlserver"


class Empresa(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    cnpj: Optional[str] = Field(default=None, index=True)
    ativa: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Escritorio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nome: str = Field(index=True)
    cnpj: Optional[str] = Field(default=None, index=True)
    cep: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nome: str
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    permissoes_csv: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    tipo_documento: TipoDocumento
    documento: str = Field(index=True)
    nome_razao: str = Field(index=True)
    email: Optional[str] = None
    telefone: Optional[str] = None
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    portal_bloqueado: bool = Field(default=False)
    portal_senha_hash: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContaPagar(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: Optional[int] = Field(default=None, foreign_key="cliente.id", index=True)
    descricao: str
    valor: float
    vencimento: date
    pago: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContaReceber(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: Optional[int] = Field(default=None, foreign_key="cliente.id", index=True)
    descricao: str
    valor: float
    vencimento: date
    recebido: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Negociacao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    titulo: str
    etapa: str
    valor_estimado: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Proposta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    titulo: str
    descricao: Optional[str] = None
    valor: float
    status: str = Field(default="rascunho")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Contrato(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    numero: str = Field(index=True)
    objeto: str
    inicio: date
    fim: Optional[date] = None
    status: str = Field(default="ativo")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Processo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    numero_processo: str = Field(index=True)
    tribunal: Optional[str] = None
    assunto: str
    status: str = Field(default="aberto")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Protocolo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    cliente_id: Optional[int] = Field(default=None, foreign_key="cliente.id", index=True)
    codigo: str = Field(index=True)
    descricao: str
    data_evento: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Campanha(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nome: str
    canal: str
    publico_alvo: Optional[str] = None
    ativa: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntegracaoCanal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    provedor: CanalIntegracao = Field(index=True)
    credenciais_json: str
    ativo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntegracaoBanco(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    banco: BancoIntegracao = Field(index=True)
    credenciais_json: str
    ativo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntegracaoBancoDados(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nome: str = Field(index=True)
    tipo: TipoBancoDados = Field(index=True)
    database_url: str
    ativo: bool = True
    principal: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
