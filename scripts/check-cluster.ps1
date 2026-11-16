$ErrorActionPreference = 'Stop'
function Check { param([string[]]$Arguments) & kubectl @Arguments; if ($LASTEXITCODE -ne 0) { throw 'Verification Kubernetes echouee' } }
Check @('-n','argocd','get','applications')
Check @('-n','demo','rollout','status','deployment/demo','--timeout=180s')
Check @('-n','monitoring','get','servicemonitors,prometheusrules')
Check @('-n','monitoring','get','pods')
Write-Host 'Completer avec les cibles UP et les alertes dans Prometheus.'
