#!/usr/bin/env python3
import paramiko
import time
import subprocess
import sys
import json
from pathlib import Path
import platform

class OneCAgentRunner:
    def __init__(self, config):
        self.config = config
        
        self.agent_host = "localhost" # В текущей реализации жестко задан
        self.agent_port = config['agent'].get('port', 1543)
        self.agent_user = config['agent'].get('ssh_user', 'admin')
        self.agent_pass = config['agent'].get('ssh_password', 'admin')
        
        self.infobase = config['infobase']['connection_string']
        self.extension_name = config['project']['extension_name']
        self.xml_path = Path(config['project']['xml_path'])
        
        # Определение пути к v8
        if platform.system() == "Windows":
             self.v8_path = Path(config['platform']['path_windows']) / config['platform']['version'] / "bin/1cv8.exe"
        else:
             self.v8_path = Path(config['platform']['path_linux']) / config['platform']['version'] / "1cv8"

        self.ssh = None
        self.shell = None
    
    def connect_to_agent(self):
        """Подключение к конфигуратору-агенту по SSH"""
        print(f"🔌 Подключение к агенту {self.agent_host}:{self.agent_port}")
        
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self.ssh.connect(
                hostname=self.agent_host,
                port=self.agent_port,
                username=self.agent_user,
                password=self.agent_pass,
                timeout=10
            )
            
            # Открываем интерактивную оболочку
            self.shell = self.ssh.invoke_shell()
            time.sleep(0.5)
            
            # Очищаем буфер приветствия
            self._read_until_prompt()
            
            print("✅ Подключено к агенту")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def _read_until_prompt(self, timeout=5):
        """Чтение до появления приглашения 'designer>'"""
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                
                if "designer>" in output:
                    return output
            time.sleep(0.1)
        
        return output
    
    def _execute_command(self, command, timeout=60):
        """Выполнение команды в SSH-консоли агента"""
        print(f"  ▶ {command}")
        
        self.shell.send(command + "\n")
        time.sleep(0.2)
        
        output = self._read_until_prompt(timeout)
        
        # Проверка на ошибки
        if "error" in output.lower() or "ошибка" in output.lower():
            print(f"  ⚠️  Возможна ошибка: {output}")
            return False
        
        print(f"  ✓ Выполнено")
        return True
    
    def load_extension_from_xml(self):
        """Загрузка расширения из XML"""
        print(f"📥 Загрузка расширения '{self.extension_name}' из {self.xml_path}")
        
        # Подключение к ИБ
        if not self._execute_command("common connect-ib"):
            return False
        
        # Загрузка конфигурации расширения
        # Для агента путь к XML должен быть локальным относительно машины с агентом
        # В данном случае предполагается что скрипт и агент на одной машине
        # TODO: Добавить поддержку SFTP если нужно копировать файлы
        abs_xml_path = self.xml_path.resolve()
        
        cmd = f"config load --name={self.extension_name} \"{abs_xml_path}\""
        if not self._execute_command(cmd, timeout=120):
            return False
        
        return True
    
    def update_db_config(self):
        """Обновление конфигурации БД"""
        print("🔄 Обновление конфигурации БД...")
        
        cmd = f"config update-db-cfg --extension={self.extension_name}"
        if not self._execute_command(cmd, timeout=120):
            return False
        
        return True
    
    def disconnect_from_ib(self):
        """Отключение от ИБ (для запуска режима предприятия)"""
        print("🔓 Отключение от ИБ...")
        return self._execute_command("common disconnect-ib")
    
    def start_debug_enterprise(self):
        """Запуск режима предприятия с отладкой"""
        print("🚀 Запуск режима предприятия с отладкой...")
        
        cmd = [
            str(self.v8_path),
            "ENTERPRISE",
            f"/S{self.infobase}",
            "/Debug",
            "/DisableStartupDialogs"
        ]
        
        # Добавляем аутентификацию если не OS Auth
        if not self.config['infobase'].get('use_os_auth', False):
             cmd.append(f"/N{self.config['infobase']['user']}")
             cmd.append(f"/P{self.config['infobase']['password']}")

        
        # Запускаем асинхронно
        is_windows = platform.system() == "Windows"
        if is_windows:
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(cmd)
        
        print("✅ Режим предприятия запущен с отладкой")
        return True
    
    def close(self):
        """Закрытие SSH-соединения"""
        if self.ssh:
            self.ssh.close()
            print("🔌 Отключено от агента")
    
    def run_full_cycle(self):
        """Полный цикл загрузки и запуска отладки"""
        print("=" * 60)
        print("🔧 1C Agent Debug Runner")
        print("=" * 60)
        
        try:
            # Подключение к агенту
            if not self.connect_to_agent():
                return False
            
            # Последовательность операций
            steps = [
                ("Загрузка XML", self.load_extension_from_xml),
                ("Обновление БД", self.update_db_config),
                ("Отключение от ИБ", self.disconnect_from_ib),
                ("Запуск отладки", self.start_debug_enterprise),
            ]
            
            for step_name, step_func in steps:
                if not step_func():
                    print(f"\n❌ Ошибка на этапе: {step_name}")
                    return False
                time.sleep(0.5)
            
            print("\n" + "=" * 60)
            print("✅ Готово! Расширение загружено, отладка запущена")
            print("💡 Нажми F5 в конфигураторе для подключения отладчика")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            return False
            
        finally:
            self.close()


def main():
    config_path = "1c_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения конфига: {e}")
        sys.exit(1)

    runner = OneCAgentRunner(config)
    success = runner.run_full_cycle()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
