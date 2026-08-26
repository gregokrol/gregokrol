. (Join-Path $PSScriptRoot "common.ps1")
Assert-Administrator
$config = Import-ServerConfig
$tailscale = Get-TailscaleExecutable

Write-Host "מתחבר ל-Tailscale..." -ForegroundColor Cyan
& $tailscale up
if ($LASTEXITCODE -ne 0) { throw "החיבור ל-Tailscale לא הושלם." }

Start-ScheduledTask -TaskName "SalHacham-API" -ErrorAction SilentlyContinue
$localReady = $false
for ($attempt = 1; $attempt -le 30; $attempt += 1) {
    try {
        $headers = @{ Authorization = "Bearer $($config.ApiToken)" }
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Headers $headers -TimeoutSec 4
        $localReady = $true
        break
    }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $localReady) { throw "שרת המחירים המקומי לא עלה. הרץ CHECK_STATUS.cmd לקבלת פרטים." }

Write-Host "פותח כתובת HTTPS מאובטחת..." -ForegroundColor Cyan
& $tailscale funnel --bg --yes 8000
if ($LASTEXITCODE -ne 0) {
    throw "Tailscale ביקש אישור להפעלת Funnel. אשר אותו בדפדפן והריץ שוב CONNECT_SITE.cmd."
}

$status = (& $tailscale status --json | ConvertFrom-Json)
$dnsName = [string]$status.Self.DNSName
if (-not $dnsName) { throw "לא התקבלה כתובת DNS מ-Tailscale." }
$serverUrl = "https://$($dnsName.TrimEnd('.'))"
Start-ScheduledTask -TaskName "SalHacham-Sync" -ErrorAction SilentlyContinue
Set-Clipboard -Value $serverUrl
$connectUrl = "$($config.SiteUrl)/?server=$([Uri]::EscapeDataString($serverUrl))"
Start-Process $connectUrl
Write-Host "כתובת השרת הועתקה ונפתח אתר סל חכם." -ForegroundColor Green
Write-Host "באתר לחץ על הכפתור 'חיבור השרת לאתר' להשלמת החיבור." -ForegroundColor Yellow
Write-Host "הסריקה הראשונה הופעלה ברקע ועלולה להימשך זמן רב." -ForegroundColor Yellow
