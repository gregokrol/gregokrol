Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:InstallRoot = Join-Path $env:ProgramData "SalHachamServer"
$script:ConfigPath = Join-Path $script:InstallRoot "windows\server-config.ps1"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "יש להפעיל את הקובץ כמנהל מערכת (Run as administrator)."
    }
}

function Import-ServerConfig {
    if (-not (Test-Path $script:ConfigPath)) {
        throw "קובץ ההגדרות של השרת חסר. יש להריץ תחילה INSTALL_SERVER.cmd."
    }
    . $script:ConfigPath
    if (-not $ApiToken -or $ApiToken.StartsWith("__")) {
        throw "חבילת ההתקנה אינה כוללת קודי חיבור תקינים."
    }
    $schedulerValue = 60
    $maxCitiesValue = 5
    $activeHoursValue = 4
    $savedHoursValue = 24
    $historyDaysValue = 30
    $telegramTokenValue = ""
    $telegramChatIdValue = ""
    $telegramCityValue = ""
    if (Get-Variable -Name SchedulerMinutes -ErrorAction SilentlyContinue) { $schedulerValue = [int]$SchedulerMinutes }
    if (Get-Variable -Name MaxCachedCities -ErrorAction SilentlyContinue) { $maxCitiesValue = [int]$MaxCachedCities }
    if (Get-Variable -Name ActiveCityRefreshHours -ErrorAction SilentlyContinue) { $activeHoursValue = [int]$ActiveCityRefreshHours }
    if (Get-Variable -Name SavedCityRefreshHours -ErrorAction SilentlyContinue) { $savedHoursValue = [int]$SavedCityRefreshHours }
    if (Get-Variable -Name PriceHistoryDays -ErrorAction SilentlyContinue) { $historyDaysValue = [int]$PriceHistoryDays }
    if (Get-Variable -Name TelegramBotToken -ErrorAction SilentlyContinue) { $telegramTokenValue = [string]$TelegramBotToken }
    if (Get-Variable -Name TelegramChatId -ErrorAction SilentlyContinue) { $telegramChatIdValue = [string]$TelegramChatId }
    if (Get-Variable -Name TelegramCity -ErrorAction SilentlyContinue) { $telegramCityValue = [string]$TelegramCity }
    return @{
        SiteUrl = $SiteUrl.TrimEnd("/")
        ApiToken = $ApiToken
        SchedulerMinutes = $schedulerValue
        MaxCachedCities = $maxCitiesValue
        ActiveCityRefreshHours = $activeHoursValue
        SavedCityRefreshHours = $savedHoursValue
        MaxPriceAgeHours = [int]$MaxPriceAgeHours
        PriceHistoryDays = $historyDaysValue
        TelegramBotToken = $telegramTokenValue
        TelegramChatId = $telegramChatIdValue
        TelegramCity = $telegramCityValue
    }
}

function Get-ServerPython {
    $python = Join-Path $script:InstallRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "סביבת Python של השרת חסרה. יש להריץ INSTALL_SERVER.cmd מחדש."
    }
    return $python
}

function Set-ServerEnvironment([hashtable]$Config) {
    $env:SAL_HACHAM_API_TOKEN = $Config.ApiToken
    $env:SAL_HACHAM_DEMO = "0"
    $env:SAL_HACHAM_MAX_AGE_HOURS = [string]$Config.MaxPriceAgeHours
    $env:SAL_HACHAM_SYNC_MINUTES = [string]$Config.SchedulerMinutes
    $env:SAL_HACHAM_MAX_CITIES = [string]$Config.MaxCachedCities
    $env:SAL_HACHAM_ACTIVE_CITY_HOURS = [string]$Config.ActiveCityRefreshHours
    $env:SAL_HACHAM_SAVED_CITY_HOURS = [string]$Config.SavedCityRefreshHours
    $env:SAL_HACHAM_HISTORY_DAYS = [string]$Config.PriceHistoryDays
    $env:SAL_HACHAM_DB = Join-Path $script:InstallRoot "data\sal_hacham.sqlite3"
    $env:SAL_HACHAM_RAW_DIR = Join-Path $script:InstallRoot "data\raw"
    $env:SAL_HACHAM_TELEGRAM_BOT_TOKEN = $Config.TelegramBotToken
    $env:SAL_HACHAM_TELEGRAM_CHAT_ID = $Config.TelegramChatId
    $env:SAL_HACHAM_TELEGRAM_CITY = $Config.TelegramCity
}

function Get-TailscaleExecutable {
    $known = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
    if (Test-Path $known) { return $known }
    $command = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw "Tailscale אינו מותקן. יש להריץ INSTALL_SERVER.cmd מחדש."
}
