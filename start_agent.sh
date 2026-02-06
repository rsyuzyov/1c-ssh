#!/bin/bash

# Чтение конфигурации с помощью jq
CONFIG_FILE="1c_config.json"

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required to parse config file. Please install it."
    exit 1
fi

PLATFORM_PATH=$(jq -r '.platform.path_linux' "$CONFIG_FILE")
PLATFORM_VERSION=$(jq -r '.platform.version' "$CONFIG_FILE")
V8_PATH="$PLATFORM_PATH/$PLATFORM_VERSION/1cv8"

CONN_STRING=$(jq -r '.infobase.connection_string' "$CONFIG_FILE")
USE_OS_AUTH=$(jq -r '.infobase.use_os_auth' "$CONFIG_FILE")
USER=$(jq -r '.infobase.user' "$CONFIG_FILE")
PASS=$(jq -r '.infobase.password' "$CONFIG_FILE")

AGENT_PORT=$(jq -r '.agent.port // 1543' "$CONFIG_FILE")
AGENT_BASE_DIR=$(jq -r '.agent.base_dir // "./agent_data"' "$CONFIG_FILE")

# Создаем директорию агента
mkdir -p "$AGENT_BASE_DIR"
ABS_AGENT_DIR=$(realpath "$AGENT_BASE_DIR")

# Формируем аргументы
ARGS=(
    "DESIGNER"
    "/S$CONN_STRING"
    "/AgentMode"
    "/AgentSSHHostKeyAuto"
    "/Visible"
    "/AgentBaseDir$ABS_AGENT_DIR"
    "/AgentPort$AGENT_PORT"
)

if [ "$USE_OS_AUTH" != "true" ]; then
    ARGS+=("/N$USER" "/P$PASS")
fi

echo "Starting 1C Designer Agent..."
echo "Path: $V8_PATH"
# echo "Arguments: ${ARGS[@]}"

"$V8_PATH" "${ARGS[@]}" &
