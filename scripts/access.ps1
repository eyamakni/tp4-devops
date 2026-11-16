param([Parameter(Mandatory=$true)][ValidateSet('argocd','grafana','prometheus','alertmanager','demo')][string]$Service)
$targets = @{
    argocd = @('argocd','argocd-server','8080:443')
    grafana = @('monitoring','monitoring-grafana','3000:80')
    prometheus = @('monitoring','monitoring-kube-prometheus-prometheus','9090:9090')
    alertmanager = @('monitoring','monitoring-kube-prometheus-alertmanager','9093:9093')
    demo = @('demo','demo','8081:8080')
}
$t = $targets[$Service]
& kubectl -n $t[0] port-forward "svc/$($t[1])" $t[2] --address 127.0.0.1
exit $LASTEXITCODE
