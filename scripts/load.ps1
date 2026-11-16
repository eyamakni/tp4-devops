param([int]$Seconds=180,[string]$Url='http://localhost:8081',[int]$DelayMilliseconds=100)
$end = (Get-Date).AddSeconds($Seconds)
$i = 0
while ((Get-Date) -lt $end) {
    $path = if ($i % 10 -eq 0) { '/error' } else { '/' }
    try { Invoke-WebRequest -UseBasicParsing -Uri "$Url$path" -TimeoutSec 5 | Out-Null }
    catch { Write-Host "Reponse attendue / erreur : $($_.Exception.Message)" }
    $i++
    Start-Sleep -Milliseconds $DelayMilliseconds
}
Write-Host "$i requetes envoyees (environ 10% de 500 volontaires)."
