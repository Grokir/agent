
# Отключение предупреждений от Pydantic об версии Python
import warnings

# Задаем жесткое "глушение" для всего
warnings.filterwarnings("ignore")
# "Ломаем" функции, которыми langchain пытается сбросить или изменить фильтры
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None



import asyncio
from time import perf_counter as timer
from datetime import datetime
from aioconsole import ainput  # Асинхронный input с поддержкой readline
import readline # импорт нуже для оперативной редакции ввода

from langchain_core.tools import tool
from kernel.kernel import kernel_init, send_prompt, memory_clear
from agent_tools.attack_generator import (
    path_to_attacks_db,
    get_attack_types,
    get_random_attack,
    get_attack_by_description,
    get_all_attacks_by_type,
    generate_custom_attack,
    send_prompt_to_mas,
    analyze_response
)
from agent_tools.workflow import save_markdown_file


async def main():
    # info()
    # run_scan(target="192.168.0.1", ports_to_scan="22,80,1900")
    tools = [
        path_to_attacks_db,
        get_attack_types,
        get_random_attack,
        get_attack_by_description,
        get_all_attacks_by_type,
        # generate_custom_attack,
        send_prompt_to_mas,
        analyze_response,
        save_markdown_file
    ]
    kernel_init(tools=tools)

    while True:
        try:
            # user_input = input("[>] Запрос: ").strip()
            user_input = await ainput("[>] Запрос: ")
            user_input = user_input.strip()
            if user_input.lower() in ("/exit", "/quit"):
                print("\n[!] Выход.")
                break
            if user_input.lower() == "/mem_clear":
                memory_clear()
                print("\n[!] Память агента очищена.")
                continue
            if user_input.lower() in ["/help", "/?"]:
                print("Выход         : '/exit' / '/quit' / Ctrl+C")
                print("Очистка памяти: '/mem_clear'")
                print("Справка       : '/help' / '/?'\n")
                continue
            if not user_input:
                continue
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H-%M")
            print(f"[!] Начало тестирования: {date_str} {time_str}")

            # Запуск агента – передаём сообщение от пользователя
            time_start = timer()
            result = await send_prompt(user_input)
            elapsed_time = timer() - time_start

            # Последнее сообщение от AI – это финальный ответ
            final_message = result["messages"][-1]
            print(f"\n[+] Время ответа: {elapsed_time:.2f} сек. Ответ агента:\n{final_message.content}\n")
        except Exception as e:
            print(f"\n[-] Ошибка: {e}")
            # 0:32 - start test

if __name__ == "__main__":
    try:
        asyncio.run(main())
        # main()
    except KeyboardInterrupt:
        print("\n[!] Выход.")
    # run(target="192.168.0.104")