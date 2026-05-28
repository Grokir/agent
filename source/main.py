from langchain_core.tools import tool
from ag_tools.nmap_scan import run_scan, run
from kernel.kernel import kernel_init, send_prompt


def main():
    # info()
    # run_scan(target="192.168.0.1", ports_to_scan="22,80,1900")
    tools = [run_scan]
    kernel_init(tools=tools)

    while True:
        try:
            user_input = input("[>] Запрос: ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            if not user_input:
                continue

            # Запуск агента – передаём сообщение от пользователя
            result = send_prompt(user_input)
            # Последнее сообщение от AI – это финальный ответ
            final_message = result["messages"][-1]
            print(f"\n[+] Ответ агента:\n{final_message.content}\n")
        except KeyboardInterrupt:
            print("\n[!] Выход.")
            break
        except Exception as e:
            print(f"[-] Ошибка: {e}")

if __name__ == "__main__":
    # main()
    run(target="192.168.0.104")