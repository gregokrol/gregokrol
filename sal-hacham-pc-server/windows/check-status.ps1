. (Join-Path $PSScriptRoot "common.ps1")
$config = Import-ServerConfig
$headers = @{ Authorization = "Bearer $($config.ApiToken)" }
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Headers $headers -TimeoutSec 5
    Write-Host "שרת מקומי: פעיל" -ForegroundColor Green
    Write-Host "סניפים במסד: $($health.real_stores) | מחירים: $($health.total_prices)"
    Write-Host "היסטוריית מחיר: $($health.history_products) מוצרים/סניפים | $($health.history_rows) סיכומים מצטברים | עד $($health.history_days) ימים"
    Write-Host "ערים שמורות: $($health.cached_city_count)/$($health.max_cached_cities) | עיר פעילה: $($health.active_city)"
    if ($health.cached_cities) {
        foreach ($city in $health.cached_cities) {
            $active = if ($city.active) { "פעילה" } else { "שמורה" }
            Write-Host "- $($city.city): $active | מצב $($city.status) | $($city.stores) סניפים | רענון אחרון $($city.last_refresh_at)"
        }
    }
}
catch {
    Write-Host "שרת מקומי: לא זמין" -ForegroundColor Red
}

try {
    $tailscale = Get-TailscaleExecutable
    $funnel = & $tailscale funnel status
    Write-Host "`nTailscale Funnel:" -ForegroundColor Cyan
    $funnel
}
catch {
    Write-Host "Tailscale Funnel: לא זמין" -ForegroundColor Red
}

$botTask = Get-ScheduledTask -TaskName "SalHacham-Bot" -ErrorAction SilentlyContinue
if ($botTask) {
    Write-Host "`nבוט טלגרם: $($botTask.State)" -ForegroundColor Cyan
} elseif ($config.TelegramBotToken -and $config.TelegramChatId) {
    Write-Host "`nבוט טלגרם: מוגדר אך לא מותקן - הרץ שוב את INSTALL_SERVER.cmd" -ForegroundColor Yellow
} else {
    Write-Host "`nבוט טלגרם: לא מוגדר" -ForegroundColor DarkGray
}

$log = Join-Path $script:InstallRoot "logs\sync.log"
if (Test-Path $log) {
    Write-Host "`nסוף יומן הסנכרון:" -ForegroundColor Cyan
    Get-Content $log -Tail 12
}
