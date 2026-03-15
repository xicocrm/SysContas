param(
    [string]$Branch = "cursor/sistema-sysconta-completo-52c3",
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

$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$installerUrl = "https://raw.githubusercontent.com/xicocrm/SysContas/$Branch/installers/windows/install_sysconta.ps1?ts=$ts"
$tempInstaller = Join-Path $env:TEMP "install_sysconta_windows.ps1"

Write-Host "Baixando instalador: $installerUrl"
Invoke-WebRequest -Uri $installerUrl -OutFile $tempInstaller -UseBasicParsing

Write-Host "Executando instalador automatico..."
& powershell -ExecutionPolicy Bypass -File $tempInstaller `
    -DeployDir $DeployDir `
    -Port $Port `
    -MaxRetries $MaxRetries `
    -RepoUrl $RepoUrl `
    -RepoBranch $RepoBranch `
    -SeedAdminEmail $SeedAdminEmail `
    -SeedAdminPassword $SeedAdminPassword `
    -SeedAdminName $SeedAdminName `
    -SeedCompanyName $SeedCompanyName `
    -SeedCompanyCnpj $SeedCompanyCnpj
