import nmap
import sys
from typing import Dict, Any
from langchain_core.tools import tool

def info():
    print("""
Простой сетевой сканер на основе Nmap (учебный пример).
Сканирует указанный хост на наиболее распространённые порты,
выводит их состояние и версии сервисов.
""")


def scan_host(target_host: str) -> Dict[str, Any]:
    # , ports: str = "22,80,443,8080,8443"
    """
    Выполняет сканирование хоста с помощью Nmap.

    :param target_host: IP-адрес или доменное имя цели.
    :param ports: строка с портами для сканирования (формат Nmap: "22,80,443" или "1-1024").
    :return: словарь с результатами сканирования (структура python-nmap).
    """
    # Создаём объект сканера
    scanner = nmap.PortScanner()

    # Аргументы Nmap:
    # -sV — определение версий служб
    # -T4 — агрессивный тайминг (ускоряет сканирование)
    # -Pn — считать хост доступным (пропустить ping-проверку)
    # arguments = f"-sV -T4 -Pn -p {ports}"
    # arguments = '-A -p- -vv --reason --script "default,safe,vuln,discovery" -T4'
    arguments = '-F -n -T5 -A'

    # print(f"[*] Запуск сканирования: {target_host} с параметрами: {arguments}")
    print(f"[*] Запуск сканирования узла ({target_host})...")
    scanner.scan(hosts=target_host, arguments=arguments)

    return scanner

   
# @tool
@tool(description="Run nmap port scan on a target IP with specified ports.")
def run_scan(target: str = "127.0.0.1") -> str:
    #, ports_to_scan: str = "1-65535"
    try:
        scan_res = ""
        scanner = scan_host(target)

        if target not in scanner.all_hosts():
            s = f"[!] Хост {target} не найден в результатах сканирования. Возможно, он недоступен или отфильтрован."
            scan_res += s
            # print(s)
            return

        host_data = scanner[target]
        s = f"Состояние: {host_data.state().upper()}"
        # print(s)
        scan_res += s

        # Перебираем протоколы (tcp/udp)
        for proto in host_data.all_protocols():
            ports = host_data[proto].keys()
            if not ports:
                s = f"Нет открытых {proto} портов"
                # print(s)
                scan_res += s
                continue

            for port in sorted(ports):
                port_info = host_data[proto][port]
                state = port_info.get('state', 'unknown')
                service = port_info.get('name', 'unknown')
                product = port_info.get('product', '')
                version = port_info.get('version', '')
                extrainfo = port_info.get('extrainfo', '')

                # Собираем полную информацию о сервисе
                service_full = service
                if product:
                    service_full += f" ({product}"
                    if version:
                        service_full += f" {version}"
                    if extrainfo:
                        service_full += f" {extrainfo}"
                    service_full += ")"

                scan_res += f"Порт {port}/{proto} {state.upper()} : {service_full}\n"
                # print(f"Порт {port}/{proto} {state.upper()} : {service_full}")

        return scan_res
    except nmap.PortScannerError as e:
        s = f"[!] Ошибка Nmap: {e}"
        # print(s)
        # print("Проверьте, установлен ли Nmap и права доступа (возможно, нужен sudo).")
        return s
    except Exception as e:
        s = f"[!] Непредвиденная ошибка: {e}"
        # print(s)
        return s

# тест флагов nmap для локального запуска без агента
def run(target: str = "127.0.0.1") -> str:
    try:
        scan_res = ""
        scanner = scan_host(target)

        if target not in scanner.all_hosts():
            s = f"[!] Хост {target} не найден в результатах сканирования. Возможно, он недоступен или отфильтрован."
            scan_res += s
            print(s)
            return

        host_data = scanner[target]
        s = f"Состояние: {host_data.state().upper()}"
        print(s)
        scan_res += s

        # Перебираем протоколы (tcp/udp)
        for proto in host_data.all_protocols():
            ports = host_data[proto].keys()
            if not ports:
                s = f"Нет открытых {proto} портов"
                print(s)
                scan_res += s
                continue

            for port in sorted(ports):
                port_info = host_data[proto][port]
                state = port_info.get('state', 'unknown')
                service = port_info.get('name', 'unknown')
                product = port_info.get('product', '')
                version = port_info.get('version', '')
                extrainfo = port_info.get('extrainfo', '')

                # Собираем полную информацию о сервисе
                service_full = service
                if product:
                    service_full += f" ({product}"
                    if version:
                        service_full += f" {version}"
                    if extrainfo:
                        service_full += f" {extrainfo}"
                    service_full += ")"

                scan_res += f"Порт {port}/{proto} {state.upper()} : {service_full}\n"
                print(f"Порт {port}/{proto} {state.upper()} : {service_full}")

        return scan_res
    except nmap.PortScannerError as e:
        s = f"[!] Ошибка Nmap: {e}"
        print(s)
        print("Проверьте, установлен ли Nmap и права доступа (возможно, нужен sudo).")
        return s
    except Exception as e:
        s = f"[!] Непредвиденная ошибка: {e}"
        print(s)
        return s