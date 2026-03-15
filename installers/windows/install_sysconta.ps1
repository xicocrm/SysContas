param(
    [string]$DeployDir = "C:\SysConta",
    [int]$Port = 8000,
    [int]$MaxRetries = 8,
    [string]$RepoUrl = "https://github.com/xicocrm/SysContas.git",
    [string]$RepoBranch = "cursor/sistema-sysconta-completo-52c3"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
            Write-Log "Falha em '$Description' ($i/$Attempts). Corrigindo e tentando novamente..."
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

    Write-Log "Chocolatey nao encontrado. Instalando automaticamente..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

function Ensure-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return
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
}

function Ensure-Nssm {
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        return
    }
    Ensure-Choco
    Invoke-WithRetry -Description "instalar NSSM" -Attempts $MaxRetries -Action {
        choco install -y nssm --no-progress
    }
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

function Configure-Service {
    param(
        [string]$ServiceName,
        [string]$PythonExe,
        [string]$AppDir,
        [int]$ServicePort
    )
    $args = "-m uvicorn app.main:app --host 0.0.0.0 --port $ServicePort"
    $nssmCmd = (Get-Command nssm).Source

    & $nssmCmd status $ServiceName *> $null
    if ($LASTEXITCODE -ne 0) {
        & $nssmCmd install $ServiceName $PythonExe $args
    }

    & $nssmCmd set $ServiceName AppDirectory $AppDir
    & $nssmCmd set $ServiceName Start SERVICE_AUTO_START
    & $nssmCmd set $ServiceName AppStdout "$AppDir\logs\sysconta.out.log"
    & $nssmCmd set $ServiceName AppStderr "$AppDir\logs\sysconta.err.log"
    & $nssmCmd set $ServiceName AppRotateFiles 1
    & $nssmCmd set $ServiceName AppRotateOnline 1
    & $nssmCmd set $ServiceName AppRotateBytes 10485760
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
            Write-Log "Healthcheck falhou ($i/20). Executando autocorrecoes..."
            try {
                Restart-Service -Name $ServiceName -Force -ErrorAction Stop
            } catch {
                Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
            }
            Start-Sleep -Seconds 3
            Repair-Pip -PythonPath $PythonExe
            & $PythonExe -m pip install -r "$AppDir\requirements.txt"
        }
    }
    throw "Nao foi possivel validar a API apos autocorrecoes."
}

try {
    Assert-Admin
    Write-Log "Iniciando instalacao automatica SysConta (Windows)..."

    $repoRoot = (Resolve-Path "$PSScriptRoot\..\.." -ErrorAction SilentlyContinue).Path
    if (-not $repoRoot -or -not (Test-Path "$repoRoot\app")) {
        if (Test-Path "$PWD\app") {
            $repoRoot = $PWD.Path
            Write-Log "Usando codigo-fonte local em $repoRoot"
        } else {
            Write-Log "Codigo-fonte local nao encontrado. Clonando automaticamente..."
            Ensure-Git
            $repoRoot = Join-Path $env:TEMP "sysconta-source"
            if (Test-Path $repoRoot) {
                Remove-Item -Path $repoRoot -Recurse -Force -ErrorAction SilentlyContinue
            }
            Invoke-WithRetry -Description "clonar repositorio" -Attempts $MaxRetries -Action {
                git clone --depth 1 --branch $RepoBranch $RepoUrl $repoRoot
            }
            if (-not (Test-Path "$repoRoot\app")) {
                throw "Repositorio clonado, mas pasta app nao foi encontrada."
            }
        }
    }

    Ensure-Python
    Ensure-Nssm

    New-Item -ItemType Directory -Path $DeployDir -Force | Out-Null
    New-Item -ItemType Directory -Path "$DeployDir\logs" -Force | Out-Null

    Invoke-WithRetry -Description "copiar codigo-fonte" -Attempts $MaxRetries -Action {
        Copy-Source -SourceDir $repoRoot -TargetDir $DeployDir
    }

    $venvDir = Join-Path $DeployDir "venv"
    $pythonExe = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path $pythonExe)) {
        Invoke-WithRetry -Description "criar virtualenv" -Attempts $MaxRetries -Action {
            python -m venv $venvDir
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

    $serviceName = "SysContaAPI"
    Invoke-WithRetry -Description "configurar servico Windows" -Attempts $MaxRetries -Action {
        Configure-Service -ServiceName $serviceName -PythonExe $pythonExe -AppDir $DeployDir -ServicePort $Port
    }

    Invoke-WithRetry -Description "iniciar servico Windows" -Attempts $MaxRetries -Action {
        Start-Service -Name $serviceName
    }

    Ensure-FirewallRule -ServicePort $Port
    Healthcheck-WithSelfHeal -ServiceName $serviceName -PythonExe $pythonExe -AppDir $DeployDir -ServicePort $Port

    Write-Log "INSTALACAO CONCLUIDA COM SUCESSO."
    Write-Log "Acesse: http://localhost:$Port/docs"
} catch {
    Write-Log "ERRO FATAL: $($_.Exception.Message)"
    exit 1
}
