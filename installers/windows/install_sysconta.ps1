param(
    [string]$DeployDir = "C:\SysConta",
    [int]$Port = 8000,
    [int]$MaxRetries = 8,
    [string]$RepoUrl = "https://github.com/xicocrm/SysContas.git",
    [string]$RepoBranch = "cursor/sistema-sysconta-completo-52c3",
    [string]$SeedAdminEmail = "admin@sysconta.com",
    [string]$SeedAdminPassword = "Admin@123456",
    [string]$SeedAdminName = "Administrador",
    [string]$SeedCompanyName = "Empresa Principal",
    [string]$SeedCompanyCnpj = "00000000000191"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $Message"
}

function Invoke-WithRetry {
    param(
        [scriptblock]$Action,
        [string]$Description,
        [int]$Attempts = 8
    )
    $sleepSeconds = 2
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            & $Action
            return
        } catch {
            if ($i -ge $Attempts) {
                throw "Falha definitiva em '$Description': $($_.Exception.Message)"
            }
            Write-Log "Falha em '$Description' ($i/$Attempts). Tentando autocorrecao..."
            Start-Sleep -Seconds $sleepSeconds
            $sleepSeconds = [Math]::Min($sleepSeconds * 2, 30)
        }
    }
}

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Execute o instalador no PowerShell como Administrador."
    }
}

function Ensure-Choco {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        return
    }
    Write-Log "Chocolatey nao encontrado. Instalando..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

function Get-PythonExe {
    try {
        $p = (& python -c "import sys; print(sys.executable)" 2>$null).Trim()
        if ($p -and (Test-Path $p)) { return $p }
    } catch {}
    try {
        $p = (& py -3 -c "import sys; print(sys.executable)" 2>$null).Trim()
        if ($p -and (Test-Path $p)) { return $p }
    } catch {}
    return $null
}

function Ensure-Python {
    $existing = Get-PythonExe
    if ($existing) {
        return $existing
    }

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Invoke-WithRetry -Description "instalar Python com winget" -Attempts $MaxRetries -Action {
            winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
        }
    } else {
        Ensure-Choco
        Invoke-WithRetry -Description "instalar Python com chocolatey" -Attempts $MaxRetries -Action {
            choco install -y python --no-progress
        }
    }

    $installed = $null
    Invoke-WithRetry -Description "detectar python instalado" -Attempts $MaxRetries -Action {
        $script:installed = Get-PythonExe
        if (-not $script:installed) { throw "python ainda indisponivel" }
    }
    return $installed
}

function Get-NssmExe {
    $cmd = Get-Command nssm -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $possible = @(
        "$env:ChocolateyInstall\bin\nssm.exe",
        "C:\ProgramData\chocolatey\bin\nssm.exe"
    )
    foreach ($path in $possible) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

function Ensure-Nssm {
    $existing = Get-NssmExe
    if ($existing) {
        return $existing
    }

    Ensure-Choco
    Invoke-WithRetry -Description "instalar NSSM" -Attempts $MaxRetries -Action {
        choco install -y nssm --no-progress
    }

    $installed = $null
    Invoke-WithRetry -Description "detectar nssm instalado" -Attempts $MaxRetries -Action {
        $script:installed = Get-NssmExe
        if (-not $script:installed) { throw "nssm ainda indisponivel" }
    }
    return $installed
}

function Ensure-Git {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        return
    }
    Ensure-Choco
    Invoke-WithRetry -Description "instalar Git" -Attempts $MaxRetries -Action {
        choco install -y git --no-progress
    }
}

function Repair-Pip {
    param([string]$PythonPath)
    & $PythonPath -m pip install --upgrade pip setuptools wheel
}

function New-Secret {
    return [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")
}

function Copy-Source {
    param(
        [string]$SourceDir,
        [string]$TargetDir
    )
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    $null = robocopy $SourceDir $TargetDir /MIR /XD .git .venv __pycache__ /XF *.pyc *.pyo
    if (($LASTEXITCODE -ge 8) -and ($LASTEXITCODE -ne $null)) {
        throw "Robocopy falhou com codigo $LASTEXITCODE"
    }
}

function Resolve-SourceRoot {
    $scriptRepo = (Resolve-Path "$PSScriptRoot\..\.." -ErrorAction SilentlyContinue).Path
    if ($scriptRepo -and (Test-Path "$scriptRepo\app")) {
        Write-Log "Usando fonte local do repositorio: $scriptRepo"
        return $scriptRepo
    }

    if (Test-Path "$($PWD.Path)\app") {
        Write-Log "Usando fonte local da pasta atual: $($PWD.Path)"
        return $PWD.Path
    }

    $downloadRoot = Join-Path $env:TEMP "sysconta-source"
    if (Test-Path $downloadRoot) {
        Remove-Item -Path $downloadRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null

    $baseUrl = $RepoUrl -replace "\.git$", ""
    $archiveUrl = "$baseUrl/archive/refs/heads/$RepoBranch.zip"
    $archiveFile = Join-Path $downloadRoot "source.zip"

    try {
        Write-Log "Baixando fonte via ZIP: $archiveUrl"
        Invoke-WithRetry -Description "download do zip do repositorio" -Attempts $MaxRetries -Action {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $archiveFile -UseBasicParsing
        }
        Expand-Archive -Path $archiveFile -DestinationPath $downloadRoot -Force
        $extracted = Get-ChildItem -Path $downloadRoot -Directory | Where-Object { $_.Name -like "SysContas-*" } | Select-Object -First 1
        if ($extracted -and (Test-Path "$($extracted.FullName)\app")) {
            Write-Log "Fonte obtida via ZIP."
            return $extracted.FullName
        }
    } catch {
        Write-Log "Falha no metodo ZIP. Tentando clone Git..."
    }

    Ensure-Git
    $gitDir = Join-Path $downloadRoot "repo"
    Invoke-WithRetry -Description "clone do repositorio" -Attempts $MaxRetries -Action {
        git clone --depth 1 --branch $RepoBranch $RepoUrl $gitDir
    }
    if (-not (Test-Path "$gitDir\app")) {
        throw "Nao foi possivel obter codigo-fonte valido."
    }
    Write-Log "Fonte obtida via Git clone."
    return $gitDir
}

function Ensure-EnvVar {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$Value
    )
    if (-not (Test-Path $FilePath)) {
        "" | Out-File -FilePath $FilePath -Encoding UTF8 -Force
    }

    $content = Get-Content $FilePath -Raw
    if ($content -match "(?m)^$Key=") {
        $escaped = [Regex]::Escape($Value)
        $content = [Regex]::Replace($content, "(?m)^$Key=.*$", "$Key=$Value")
        Set-Content -Path $FilePath -Value $content -Encoding UTF8
    } else {
        Add-Content -Path $FilePath -Value "$Key=$Value"
    }
}

function Seed-Admin {
    param(
        [string]$PythonExe,
        [string]$AppDir
    )

    $moduleFile = Join-Path $AppDir "app\scripts\ensure_admin.py"
    if (Test-Path $moduleFile) {
        try {
            & $PythonExe -m app.scripts.ensure_admin
            Write-Log "Admin inicial configurado (modulo)."
            return
        } catch {
            Write-Log "Falha ao usar modulo de seed. Aplicando fallback inline..."
        }
    } else {
        Write-Log "Modulo de seed ausente. Aplicando fallback inline..."
    }

    $seedScript = @"
import os, sys
from pathlib import Path
from passlib.context import CryptContext
from sqlmodel import SQLModel, Session, create_engine, select
sys.path.insert(0, os.getcwd())
from app.models import Empresa, User

def read_database_url():
    env_file = Path(".env")
    if not env_file.exists():
        return "sqlite:///./sysconta.db"
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip() or "sqlite:///./sysconta.db"
    return "sqlite:///./sysconta.db"

db = read_database_url()
connect_args = {"check_same_thread": False} if db.startswith("sqlite") else {}
engine = create_engine(db, connect_args=connect_args)
SQLModel.metadata.create_all(engine)
pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

admin_name = os.getenv("SEED_ADMIN_NAME", "Administrador")
admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@sysconta.com").strip().lower()
admin_password = os.getenv("SEED_ADMIN_PASSWORD", "Admin@123456")
company_name = os.getenv("SEED_COMPANY_NAME", "Empresa Principal")
company_cnpj = os.getenv("SEED_COMPANY_CNPJ", "00000000000191")

with Session(engine) as s:
    company = None
    if company_cnpj:
        company = s.exec(select(Empresa).where(Empresa.cnpj == company_cnpj)).first()
    if not company:
        company = s.exec(select(Empresa).where(Empresa.nome == company_name)).first()
    if not company:
        company = Empresa(nome=company_name, cnpj=company_cnpj or None, ativa=True)
        s.add(company); s.commit(); s.refresh(company)

    user = s.exec(select(User).where(User.email == admin_email)).first()
    if user:
        user.nome = admin_name
        user.empresa_id = company.id
        user.is_active = True
        user.is_superuser = True
        user.hashed_password = pwd.hash(admin_password)
        s.add(user)
    else:
        user = User(
            empresa_id=company.id,
            nome=admin_name,
            email=admin_email,
            hashed_password=pwd.hash(admin_password),
            is_active=True,
            is_superuser=True,
            permissoes_csv=""
        )
        s.add(user)
    s.commit()
print("admin_ok")
"@

    Push-Location $AppDir
    try {
        & $PythonExe -c $seedScript
        Write-Log "Admin inicial configurado (fallback)."
    } finally {
        Pop-Location
    }
}

function Configure-Service {
    param(
        [string]$ServiceName,
        [string]$PythonExe,
        [string]$AppDir,
        [int]$ServicePort,
        [string]$NssmExe
    )
    $args = "-m uvicorn app.main:app --host 0.0.0.0 --port $ServicePort"

    & $NssmExe status $ServiceName *> $null
    if ($LASTEXITCODE -ne 0) {
        & $NssmExe install $ServiceName $PythonExe $args
    }

    & $NssmExe set $ServiceName AppDirectory $AppDir
    & $NssmExe set $ServiceName Start SERVICE_AUTO_START
    & $NssmExe set $ServiceName AppStdout "$AppDir\logs\sysconta.out.log"
    & $NssmExe set $ServiceName AppStderr "$AppDir\logs\sysconta.err.log"
    & $NssmExe set $ServiceName AppRotateFiles 1
    & $NssmExe set $ServiceName AppRotateOnline 1
    & $NssmExe set $ServiceName AppRotateBytes 10485760
}

function Start-Or-RestartService {
    param([string]$ServiceName)
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        throw "Servico '$ServiceName' nao encontrado."
    }
    if ($service.Status -eq "Running") {
        Restart-Service -Name $ServiceName -Force
    } else {
        Start-Service -Name $ServiceName
    }
}

function Ensure-FirewallRule {
    param([int]$ServicePort)
    $ruleName = "SysConta API $ServicePort"
    $rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $rule) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $ServicePort -Protocol TCP -Action Allow | Out-Null
    }
}

function Healthcheck-WithSelfHeal {
    param(
        [string]$ServiceName,
        [string]$PythonExe,
        [string]$AppDir,
        [int]$ServicePort
    )
    for ($i = 1; $i -le 20; $i++) {
        try {
            $result = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$ServicePort/health" -TimeoutSec 10
            if ($result.status -eq "ok") {
                Write-Log "Healthcheck da API OK."
                return
            }
        } catch {
            Write-Log "Healthcheck falhou ($i/20). Aplicando autocorrecao..."
            try {
                Start-Or-RestartService -ServiceName $ServiceName
            } catch {
                Write-Log "Falha ao reiniciar servico: $($_.Exception.Message)"
            }
            Start-Sleep -Seconds 3
            Repair-Pip -PythonPath $PythonExe
            & $PythonExe -m pip install -r "$AppDir\requirements.txt"
        }
    }
    throw "Nao foi possivel validar a API apos autocorrecoes."
}

function Test-InitialLogin {
    param(
        [int]$ServicePort,
        [string]$Email,
        [string]$Password
    )
    try {
        $payload = "username=$([uri]::EscapeDataString($Email))&password=$([uri]::EscapeDataString($Password))"
        $resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$ServicePort/auth/login" -ContentType "application/x-www-form-urlencoded" -Body $payload -TimeoutSec 15
        return [bool]$resp.access_token
    } catch {
        return $false
    }
}

try {
    Assert-Admin
    Write-Log "Iniciando instalacao automatica SysConta (Windows)..."

    $sourceRoot = Resolve-SourceRoot
    $pythonBootstrap = Ensure-Python
    $nssmExe = Ensure-Nssm

    New-Item -ItemType Directory -Path $DeployDir -Force | Out-Null
    New-Item -ItemType Directory -Path "$DeployDir\logs" -Force | Out-Null

    Invoke-WithRetry -Description "copiar codigo-fonte" -Attempts $MaxRetries -Action {
        Copy-Source -SourceDir $sourceRoot -TargetDir $DeployDir
    }

    $venvDir = Join-Path $DeployDir "venv"
    $pythonExe = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path $pythonExe)) {
        Invoke-WithRetry -Description "criar virtualenv" -Attempts $MaxRetries -Action {
            & $pythonBootstrap -m venv $venvDir
        }
    }

    Invoke-WithRetry -Description "upgrade pip/setuptools/wheel" -Attempts $MaxRetries -Action {
        Repair-Pip -PythonPath $pythonExe
    }

    Invoke-WithRetry -Description "instalar dependencias" -Attempts $MaxRetries -Action {
        & $pythonExe -m pip install -r "$DeployDir\requirements.txt"
    }

    $envFile = Join-Path $DeployDir ".env"
    if (-not (Test-Path $envFile)) {
        $secret = New-Secret
@"
APP_NAME=SysConta API
ENVIRONMENT=prod
SECRET_KEY=$secret
TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sysconta.db
"@ | Out-File -FilePath $envFile -Encoding UTF8 -Force
    }

    Ensure-EnvVar -FilePath $envFile -Key "AUTO_SEED_ADMIN" -Value "true"
    Ensure-EnvVar -FilePath $envFile -Key "SEED_ADMIN_NAME" -Value $SeedAdminName
    Ensure-EnvVar -FilePath $envFile -Key "SEED_ADMIN_EMAIL" -Value $SeedAdminEmail
    Ensure-EnvVar -FilePath $envFile -Key "SEED_ADMIN_PASSWORD" -Value $SeedAdminPassword
    Ensure-EnvVar -FilePath $envFile -Key "SEED_COMPANY_NAME" -Value $SeedCompanyName
    Ensure-EnvVar -FilePath $envFile -Key "SEED_COMPANY_CNPJ" -Value $SeedCompanyCnpj

    Invoke-WithRetry -Description "criar/ajustar admin inicial" -Attempts $MaxRetries -Action {
        Seed-Admin -PythonExe $pythonExe -AppDir $DeployDir
    }

    $serviceName = "SysContaAPI"
    Invoke-WithRetry -Description "configurar servico Windows" -Attempts $MaxRetries -Action {
        Configure-Service -ServiceName $serviceName -PythonExe $pythonExe -AppDir $DeployDir -ServicePort $Port -NssmExe $nssmExe
    }

    Invoke-WithRetry -Description "iniciar/reiniciar servico Windows" -Attempts $MaxRetries -Action {
        Start-Or-RestartService -ServiceName $serviceName
    }

    Ensure-FirewallRule -ServicePort $Port
    Healthcheck-WithSelfHeal -ServiceName $serviceName -PythonExe $pythonExe -AppDir $DeployDir -ServicePort $Port

    if (-not (Test-InitialLogin -ServicePort $Port -Email $SeedAdminEmail -Password $SeedAdminPassword)) {
        Write-Log "Login inicial falhou no teste. Reaplicando seed e reiniciando..."
        Seed-Admin -PythonExe $pythonExe -AppDir $DeployDir
        Start-Or-RestartService -ServiceName $serviceName
        Start-Sleep -Seconds 2
    }

    $loginOk = Test-InitialLogin -ServicePort $Port -Email $SeedAdminEmail -Password $SeedAdminPassword
    if (-not $loginOk) {
        throw "Instalacao concluida sem erro de servico, mas o login inicial falhou."
    }

    Write-Log "INSTALACAO CONCLUIDA COM SUCESSO."
    Write-Log "Login inicial: $SeedAdminEmail / $SeedAdminPassword"
    Write-Log "Sistema: http://localhost:$Port/"
    Write-Log "API docs: http://localhost:$Port/docs"
} catch {
    Write-Log "ERRO FATAL: $($_.Exception.Message)"
    exit 1
}
