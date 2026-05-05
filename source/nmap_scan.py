
import nmap
import sys
from typing import Dict, Any

def info():
    print("""
Простой сетевой сканер на основе Nmap (учебный пример).
Сканирует указанный хост на наиболее распространённые порты,
выводит их состояние и версии сервисов.
""")


def scan_host(target_host: str, ports: str = "22,80,443,8080,8443") -> Dict[str, Any]:
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
    arguments = '-A -p- -vv --reason --script "default,safe,vuln,discovery" -T4'

    # print(f"[*] Запуск сканирования: {target_host} с параметрами: {arguments}")
    print(f"[*] Запуск сканирования узла ({target_host})...")
    scanner.scan(hosts=target_host, arguments=arguments)

    return scanner

def print_results(scanner: nmap.PortScanner, target_host: str) -> None:
    """
    Выводит сводку по результатам сканирования в удобочитаемом виде.

    :param scanner: объект PortScanner с результатами.
    :param target_host: хост, для которого выводится информация.
    """
    # Проверяем, есть ли хост в результатах
   

def run(target: str = "127.0.0.1", ports_to_scan: str = "1-65535") -> str:
    try:
        scan_res = ""
        scanner = scan_host(target, ports_to_scan)


        if target not in scanner.all_hosts():
            print(f"[!] Хост {target} не найден в результатах сканирования. "
              "Возможно, он недоступен или отфильтрован.")
            return

        host_data = scanner[target]
        print(f"Состояние: {host_data.state().upper()}")

        # Перебираем протоколы (tcp/udp)
        for proto in host_data.all_protocols():
            ports = host_data[proto].keys()
            if not ports:
                print(f"Нет открытых {proto} портов")
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


    except nmap.PortScannerError as e:
        print(f"[!] Ошибка Nmap: {e}")
        print("Проверьте, установлен ли Nmap и права доступа (возможно, нужен sudo).")
    except Exception as e:
        print(f"[!] Непредвиденная ошибка: {e}")
