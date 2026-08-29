$SiteUrl = "https://sal-hacham.fastnadlan.chatgpt.site"
$ApiToken = "__PC_API_TOKEN__"
$SchedulerMinutes = 60
$MaxCachedCities = 5
$ActiveCityRefreshHours = 4
$SavedCityRefreshHours = 24
$MaxPriceAgeHours = 5
$PriceHistoryDays = 30

# Optional: Telegram bot for price-drop alerts and remote /search, /basket, /status
# commands. Leave TelegramBotToken empty to keep the bot disabled.
# The bot token is a secret - never commit the real one. Get it from @BotFather
# and set it only in the local (gitignored) windows/server-config.ps1.
$TelegramBotToken = ""
# Chat id is not sensitive by itself (useless without the token above), so this
# one is a real personal default: Gregori's "סל חכם" bot chat.
$TelegramChatId = "544409710"
$TelegramCity = ""
