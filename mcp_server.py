#!/usr/bin/env python3
import asyncio
import json
from mcp.server import Server
from mcp.types import Tool, TextContent
from pathlib import Path

# Импортируем наш класс
from agent_runner import OneCAgentRunner

app = Server("1c-debug-server")

CONFIG_PATH = "1c_config.json"

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="load_and_debug_extension",
            description="Загружает расширение 1С из XML, обновляет БД и запускает отладку. Использует настройки из 1c_config.json",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "load_and_debug_extension":
        try:
            config = load_config()
            if not config:
                 return [TextContent(
                    type="text",
                    text="❌ Ошибка: Не удалось загрузить конфигурацию из 1c_config.json"
                )]

            runner = OneCAgentRunner(config)
            
            success = runner.run_full_cycle()
            
            if success:
                return [TextContent(
                    type="text",
                    text="✅ Расширение загружено, БД обновлена, отладка запущена"
                )]
            else:
                return [TextContent(
                    type="text",
                    text="❌ Ошибка при выполнении операций. Проверь логи."
                )]
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Ошибка: {str(e)}"
            )]
    
    return [TextContent(type="text", text="Unknown tool")]

async def main():
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
