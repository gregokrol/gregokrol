Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $PSScriptRoot
$commonSource = Join-Path $PSScriptRoot "common.ps1"
. $commonSource
Assert-Administrator

$sourceConfig = Join-Path $PSScriptRoot "server-config.ps1"
if (-not (Test-Path $sourceConfig)) {
    throw "קובץ server-config.ps1 חסר בחבילה. הורד מחדש את החבילה המוכנה."
}
$sourceText = Get-Content $sourceConfig -Raw
if ($sourceText.Contains("__PC_API_TOKEN__")) {
    throw "זו חבילת מקור ללא קודי חיבור. יש להשתמש בחבילה האישית שנוצרה עבור האתר."
}

$drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($env:ProgramData).TrimEnd("\").TrimEnd(":"))
if ($drive.Free -lt (10 * 1024 * 1024 * 1024)) {
    throw "נדרשים לפחות 10GB פנויים בכונן המערכת למטמון של עד חמש ערים."
}

if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
    throw "Windows Package Manager (winget) חסר. עדכן את App Installer מחנות Microsoft ונסה שוב."
}

function Resolve-SystemPython {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $launcherPath = $launcher.Source
        $path = & $launcherPath -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $path) { return $path.Trim() }
    }
    $known = Join-Path $env:LocalAppData "Programs\Python\Python312\python.exe"
    if (Test-Path $known) { return $known }
    return $null
}

$python = Resolve-SystemPython
if (-not $python) {
    Write-Host "מתקין Python 3.12..." -ForegroundColor Cyan
    winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "התקנת Python נכשלה." }
    $python = Resolve-SystemPython
}
if (-not $python) { throw "Python הותקן אך לא אותר. הפעל מחדש את המחשב והריץ שוב את ההתקנה." }

$tailscalePath = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
if (-not (Test-Path $tailscalePath)) {
    Write-Host "מתקין Tailscale..." -ForegroundColor Cyan
    winget install --id Tailscale.Tailscale --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "התקנת Tailscale נכשלה." }
}

Write-Host "מעתיק את קבצי השרת..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $script:InstallRoot -Force | Out-Null
$preservedData = Join-Path $script:InstallRoot "data"
$preservedVenv = Join-Path $script:InstallRoot ".venv"
Get-ChildItem $packageRoot -Force | Where-Object { $_.Name -notin @("data", ".venv") } | ForEach-Object {
    Copy-Item $_.FullName -Destination $script:InstallRoot -Recurse -Force
}
$currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $script:ConfigPath /inheritance:r /grant:r "*S-1-5-18:(F)" "*S-1-5-32-544:(F)" "*$($currentSid):(R)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "הגנת קובץ החיבור נכשלה." }
New-Item -ItemType Directory -Path $preservedData -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $preservedData "raw") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $script:InstallRoot "logs") -Force | Out-Null

if (-not (Test-Path (Join-Path $preservedVenv "Scripts\python.exe"))) {
    & $python -m venv $preservedVenv
    if ($LASTEXITCODE -ne 0) { throw "יצירת סביבת Python נכשלה." }
}
$serverPython = Join-Path $preservedVenv "Scripts\python.exe"
Write-Host "מתקין את רכיבי איסוף המחירים..." -ForegroundColor Cyan
& $serverPython -m pip install --disable-pip-version-check --upgrade pip
& $serverPython -m pip install --disable-pip-version-check -r (Join-Path $script:InstallRoot "requirements.txt") -r (Join-Path $script:InstallRoot "requirements-live.txt")
if ($LASTEXITCODE -ne 0) { throw "התקנת רכיבי Python נכשלה." }

$taskUser = "SYSTEM"
$apiAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script:InstallRoot\windows\start-api.ps1`""
$apiTrigger = New-ScheduledTaskTrigger -AtStartup
$apiSettings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "SalHacham-API" -Action $apiAction -Trigger $apiTrigger -Settings $apiSettings -User $taskUser -RunLevel Highest -Force | Out-Null

$syncAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script:InstallRoot\windows\sync-once.ps1`""
$syncTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 60) -RepetitionDuration (New-TimeSpan -Days 3650)
$syncSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 12) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "SalHacham-Sync" -Action $syncAction -Trigger $syncTrigger -Settings $syncSettings -User $taskUser -RunLevel Highest -Force | Out-Null

Start-ScheduledTask -TaskName "SalHacham-API"
Write-Host "ההתקנה המקומית הסתיימה." -ForegroundColor Green
Write-Host "כעת ייפתח שלב החיבור המאובטח לאתר." -ForegroundColor Cyan
& (Join-Path $script:InstallRoot "windows\connect-site.ps1")
