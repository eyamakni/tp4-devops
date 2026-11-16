param([string]$Context = 'kind-tp4-gitops', [switch]$CreateCluster)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Invoke-Checked { param([string]$Exe, [string[]]$Arguments) & $Exe @Arguments; if ($LASTEXITCODE -ne 0) { throw "$Exe a echoue ($LASTEXITCODE)" } }
Invoke-Checked docker @('info','--format','{{.ServerVersion}}')
if ($CreateCluster) {
    if ($Context -ne 'kind-tp4-gitops') { throw 'CreateCluster exige kind-tp4-gitops.' }
    $clusters = & kind get clusters
    if ($LASTEXITCODE -ne 0) { throw 'kind get clusters a echoue' }
    if ($clusters -notcontains 'tp4-gitops') {
        Invoke-Checked kind @('create','cluster','--name','tp4-gitops','--image','kindest/node:v1.32.2','--wait','120s')
    }
}
Invoke-Checked kubectl @('config','use-context',$Context)
Invoke-Checked kubectl @('cluster-info','--request-timeout=10s')
Invoke-Checked kubectl @('apply','--server-side','--force-conflicts','-k','bootstrap/argocd')
Invoke-Checked kubectl @('wait','--for=condition=Established','crd/applications.argoproj.io','--timeout=120s')
Invoke-Checked kubectl @('-n','argocd','rollout','status','deployment/argocd-server','--timeout=300s')
Invoke-Checked kubectl @('apply','-f','argocd/monitoring.yaml')
Invoke-Checked kubectl @('apply','-f','argocd/demo.yaml')
# Attendre que l'application Helm ait cree les CRD, avant les ressources custom.
$deadline = (Get-Date).AddMinutes(10)
do {
    $crd = & kubectl get crd servicemonitors.monitoring.coreos.com --ignore-not-found -o name
    $ready = ($LASTEXITCODE -eq 0) -and [bool]$crd
    if (-not $ready) { Start-Sleep -Seconds 5 }
} until ($ready -or (Get-Date) -ge $deadline)
if (-not $ready) { throw 'CRD ServiceMonitor absente apres 10 minutes. Verifier monitoring dans ArgoCD.' }
Invoke-Checked kubectl @('wait','--for=condition=Established','crd/servicemonitors.monitoring.coreos.com','--timeout=120s')
Invoke-Checked kubectl @('wait','--for=condition=Established','crd/prometheusrules.monitoring.coreos.com','--timeout=120s')
Invoke-Checked kubectl @('apply','-f','argocd/observability.yaml')
Write-Host 'Bootstrap termine. Suivre : kubectl -n argocd get applications -w'
