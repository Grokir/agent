import asyncio
from aioconsole import ainput  # Асинхронный input с поддержкой readline
import readline # импорт нуже для оперативной редакции ввода

from langchain_core.tools import tool
from kernel.kernel import kernel_init, send_prompt
from agent_tools.attack_generator import (
    get_attack_types,
    get_random_attack,
    get_attack_by_description,
    get_all_attacks_by_type,
    generate_custom_attack,
    send_prompt_to_mas,
    analyze_response
)


async def main():
    # info()
    # run_scan(target="192.168.0.1", ports_to_scan="22,80,1900")
    tools = [
        get_attack_types,
        get_random_attack,
        get_attack_by_description,
        get_all_attacks_by_type,
        generate_custom_attack,
        send_prompt_to_mas,
        analyze_response
    ]
    kernel_init(tools=tools)

    while True:
        try:
            # user_input = input("[>] Запрос: ").strip()
            user_input = await ainput("[>] Запрос: ")
            user_input = user_input.strip()
            if user_input.lower() in ("exit", "quit"):
                print("\n[!] Выход.")
                break
            if user_input.lower() == "help":
                print("Выход  : 'exit' / 'quit' / Ctrl+C")
                print("Справка: 'help'\n")
                continue
            if not user_input:
                continue

            # Запуск агента – передаём сообщение от пользователя
            result = await send_prompt(user_input)
            # Последнее сообщение от AI – это финальный ответ
            final_message = result["messages"][-1]
            print(f"\n[+] Ответ агента:\n{final_message.content}\n")
        except KeyboardInterrupt:
            print("\n[!] Выход.")
            break
        except Exception as e:
            print(f"\n[-] Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    # main()
    # run(target="192.168.0.104")