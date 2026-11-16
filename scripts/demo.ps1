param([Parameter(Mandatory=$true)][ValidateSet('scale','break','restore','drift','status')][string]$Action,[int]$Replicas=4)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Action -eq 'drift') {
    & kubectl -n demo scale deployment/demo --replicas=1
    if ($LASTEXITCODE -ne 0) { throw 'Echec du drift' }
    Write-Host 'Observer ArgoCD et kubectl -n demo get deployment -w'
    exit 0
}
if ($Action -eq 'status') {
    & kubectl -n argocd get applications
    & kubectl -n demo get deployment,pods
    exit $LASTEXITCODE
}
$file = Join-Path (Get-Location) 'apps/demo/overlays/dev/kustomization.yaml'
$text = [IO.File]::ReadAllText($file)
switch ($Action) {
    'scale' { if ($Replicas -lt 1 -or $Replicas -gt 10) { throw 'Replicas : 1..10' }; $text = $text -replace 'count: \d+', "count: $Replicas" }
    'break' { $text = $text -replace 'newTag: .*', 'newTag: tp4-image-inexistante' }
    'restore' { $text = $text -replace 'newTag: .*', 'newTag: 3.12.12-slim-bookworm' }
}
[IO.File]::WriteAllText($file, $text, [Text.UTF8Encoding]::new($false))
Write-Host 'Modification locale prete. Relire, puis executer :'
Write-Host 'git diff'
Write-Host 'git add apps/demo/overlays/dev/kustomization.yaml'
Write-Host "git commit -m 'demo: $Action'"
Write-Host 'git push origin main'
