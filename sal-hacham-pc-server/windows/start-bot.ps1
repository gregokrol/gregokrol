. (Join-Path $PSScriptRoot "common.ps1")
$config = Import-ServerConfig
if (-not $config.TelegramBotToken -or -not $config.TelegramChatId) {
    Write-Host "Telegram not configured (TelegramBotToken/TelegramChatId empty); bot task exiting." -ForegroundColor Yellow
    exit 0
}
Set-ServerEnvironment $config
$python = Get-ServerPython
$logs = Join-Path $script:InstallRoot "logs"
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$log = Join-Path $logs "bot.log"
Set-Location $script:InstallRoot
"[$(Get-Date -Format s)] Starting Telegram bot" | Out-File -FilePath $log -Append -Encoding utf8
& $python -m app.telegram_bot *>> $log
exit $LASTEXITCODE
