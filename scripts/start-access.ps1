$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$logs = Join-Path $root 'artifacts'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
foreach ($service in @('argocd','grafana','prometheus','alertmanager','demo')) {
    $script = Join-Path $PSScriptRoot 'access.ps1'
    $p = Start-Process powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + $script + '"'),$service) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs "$service.out.log") -RedirectStandardError (Join-Path $logs "$service.err.log")
    Write-Host "$service : processus $($p.Id)"
}
Write-Host 'Acces locaux lances. Logs : artifacts/'
