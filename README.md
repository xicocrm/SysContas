# SysConta API (MVP Profissional)

Backend base para um sistema **SysConta** com foco em:

- Multiempresa e multiusuário
- Gestão de usuários e permissões por módulo
- Cadastro completo de escritórios e clientes (CPF/CNPJ)
- Busca automática de dados por CNPJ (fonte pública) e endereço por CEP
- Contas a pagar e receber
- Negociações, propostas, contratos
- Processos e protocolos
- Campanhas
- Portal do cliente (acesso por CPF/CNPJ + senha, com bloqueio)
- Notificações por e-mail e WhatsApp (via integrações cadastradas)
- Estrutura de integrações com canais e bancos
- Integração com bancos de dados para armazenamento da aplicação

## Módulos disponíveis

- `Auth`: autenticação JWT, bootstrap de admin e cadastro de usuários
- `Empresas`: empresas e escritórios
- `Clientes`: cadastro com CPF/CNPJ, lookup CNPJ/CEP, bloqueio de portal
- `Financeiro`: contas a pagar/receber e resumo financeiro
- `Comercial`: negociações, propostas e contratos
- `Jurídico`: processos e protocolos
- `Campanhas`: campanhas de comunicação
- `Integrações`: canais e bancos
- `Portal`: login do cliente e consulta de contas a receber
- `Configurações`: permissões de usuários + integração de banco de dados
- `Notificações`: envio integrado (MVP)

## Integrações suportadas (cadastro)

### Canais/API

- wavoip
- a-api
- fale_paco
- wlaticket
- whatsapp
- facebook
- instagram

### Bancos/gateways

- asaas
- inter
- efi
- cora
- mercado_pago
- pagbank
- bradesco
- itau
- banco_do_brasil
- caixa

> Observação: a estrutura de credenciais e ativação está pronta. A chamada transacional de cada fornecedor pode ser plugada no serviço correspondente.

## Executar localmente

### 1) Criar ambiente e instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
```

### 2) Rodar API

```bash
uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`

## Instalador completo automatico (VPS e Windows)

O projeto agora inclui instaladores com:

- instalacao automatica de dependencias
- retries com backoff exponencial
- autocorrecao em falhas comuns
- healthcheck final obrigatorio
- continuidade automatica da instalacao ate concluir com sucesso

### VPS Linux (Ubuntu/Debian)

Arquivo: `installers/vps/install_sysconta.sh`

```bash
sudo bash installers/vps/install_sysconta.sh
```

Variaveis opcionais:

- `APP_PORT` (padrao: `8000`)
- `DOMAIN` (padrao: `_`)
- `DEPLOY_ROOT` (padrao: `/opt/sysconta`)
- `SYSCONTA_REPO_URL` (usa clone automatico se a pasta atual nao tiver o codigo)
- `MAX_RETRIES` (padrao: `8`)

O instalador Linux faz automaticamente:

- apt repair (`dpkg --configure -a`, `apt-get install -f`)
- instalacao de Python, Nginx, Git, OpenSSL e utilitarios
- virtualenv + instalacao de requirements
- criacao de `.env` com `SECRET_KEY`
- configuracao de `systemd` para API
- configuracao de Nginx reverse proxy
- healthcheck da API
- fallback automatico para Docker se o modo nativo falhar

### Windows Server

Arquivo: `installers/windows/install_sysconta.ps1`

Execute no PowerShell como Administrador:

```powershell
powershell -ExecutionPolicy Bypass -File .\installers\windows\install_sysconta.ps1
```

Parametros opcionais:

- `-DeployDir "C:\SysConta"`
- `-Port 8000`
- `-MaxRetries 8`

O instalador Windows faz automaticamente:

- instalacao do Python (winget/chocolatey)
- instalacao do NSSM para servico Windows
- copia/sincronizacao de codigo para pasta de deploy
- virtualenv + requirements
- criacao de `.env` com `SECRET_KEY`
- criacao e inicializacao de servico `SysContaAPI`
- regra de firewall para porta da API
- healthcheck com autocorrecao (restart de servico + reinstall deps)

## Configuração por variáveis de ambiente

Crie um arquivo `.env`:

```env
APP_NAME=SysConta API
ENVIRONMENT=prod
SECRET_KEY=troque-esta-chave-em-producao
TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sysconta.db
```

## Integração com bancos de dados (Configurações)

Agora o módulo de configurações possui endpoints para:

- Cadastrar conexões de banco de dados por empresa
- Testar conexão (`SELECT 1`)
- Definir conexão principal
- Aplicar conexão como armazenamento ativo da aplicação
- Persistir `DATABASE_URL` automaticamente no `.env` (opcional)

Tipos suportados:

- sqlite
- postgresql (driver `psycopg`)
- mysql / mariadb (driver `pymysql`)
- sqlserver (requer driver ODBC no servidor)

Endpoints principais:

- `GET /configuracoes/bancos-dados/tipos`
- `POST /configuracoes/bancos-dados`
- `GET /configuracoes/{empresa_id}/bancos-dados`
- `POST /configuracoes/bancos-dados/{integracao_id}/testar`
- `POST /configuracoes/bancos-dados/{integracao_id}/aplicar-armazenamento`
- `GET /configuracoes/armazenamento-ativo`

## Fluxo inicial recomendado

1. Criar empresa em `POST /empresas`
2. Executar bootstrap de admin em `POST /auth/bootstrap`
3. Fazer login admin em `POST /auth/login`
4. Criar usuários com permissões em `POST /auth/users`
5. Cadastrar integrações em `/integracoes/canais` e `/integracoes/bancos`
6. Cadastrar clientes por CPF/CNPJ em `/clientes`

## Segurança e boas práticas implementadas

- JWT para autenticação
- Hash de senha com bcrypt
- Isolamento por empresa (tenant)
- Controle de permissões por módulo
- Portal do cliente com bloqueio manual

## Deploy em VPS (Linux) e Windows

### VPS Linux (recomendado)

- Usar `systemd` + `uvicorn`/`gunicorn` atrás de `Nginx`
- Banco recomendado para produção: PostgreSQL
- Ativar HTTPS com certbot
- Definir `SECRET_KEY` forte e segredos de integração via variáveis de ambiente

### Windows Server

- Rodar com `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Configurar serviço com NSSM/Task Scheduler
- Reverse proxy com IIS (ARR) se necessário

## Próximos passos (produção enterprise)

- Migrations com Alembic
- Auditoria detalhada e trilhas LGPD
- Fila de jobs (Celery/RQ) para notificações
- Integrações transacionais completas (Asaas, Inter, WhatsApp APIs etc.)
- Frontend web e app com UX completa
