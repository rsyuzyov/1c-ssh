# Чтение конфигурации из JSON
$config = Get-Content -Raw -Path "1c_config.json" | ConvertFrom-Json

$v8Path = Join-Path $config.platform.path_windows "$($config.platform.version)\bin\1cv8.exe"

# Формирование аргументов
$argsList = @(
    "DESIGNER",
    "/S`"$($config.infobase.connection_string)`"",
    "/AgentMode",
    "/AgentSSHHostKeyAuto",
    "/Visible"
)

# Добавление аутентификации если не используется OS Auth
if (-not $config.infobase.use_os_auth) {
    $argsList += "/N`"$($config.infobase.user)`""
    $argsList += "/P`"$($config.infobase.password)`""
}

# Дополнительные параметры агента
if ($config.agent.base_dir) {
    # Создаем директорию если не существует
    if (-not (Test-Path $config.agent.base_dir)) {
        New-Item -ItemType Directory -Path $config.agent.base_dir | Out-Null
    }
    # Преобразуем относительный путь в абсолютный
    $absPath = Resolve-Path $config.agent.base_dir
    $argsList += "/AgentBaseDir`"$absPath`""
}

if ($config.agent.port) {
    $argsList += "/AgentPort$($config.agent.port)"
}

Write-Host "Starting 1C Designer Agent..."
Write-Host "Path: $v8Path"
Write-Host "Arguments: $argsList"

Start-Process $v8Path -ArgumentList $argsList
