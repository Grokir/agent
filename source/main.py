# Отключение предупреждений от Pydantic об версии Python
import warnings

# Задаем жесткое "глушение" для всего
warnings.filterwarnings("ignore")
# "Ломаем" функции, которыми langchain пытается сбросить или изменить фильтры
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None



import asyncio
import re
from time import perf_counter as timer
from datetime import datetime
from aioconsole import ainput  # Асинхронный input с поддержкой readline
import readline # импорт нуже для оперативной редакции ввода

from langchain_core.tools import tool
from kernel.kernel import kernel_init, send_prompt, memory_clear
from agent_tools.attack_generator import (
    TARGET_MAS_URL,
    # path_to_attacks_db,
    get_attack_types,
    get_random_attack,
    get_attack_by_description,
    get_all_attacks_by_type,
    get_attack_by_type_and_id,
    generate_custom_attack,
    send_prompt_to_mas,
    analyze_response,
    reset_last_interaction,
    check_mas_available,
    MasUnavailableError,
)
from agent_tools.workflow import save_markdown_file, record_attack_result, clear_report_records, set_expected_count, get_expected_count, check_expected_count


def _parse_expected_count(text: str):
    """Достаёт N из запроса вида 'tag=...; N=5' (регистр и пробелы вокруг '=' не важны)."""
    m = re.search(r"\bN\s*=\s*(\d+)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


async def main():
    # info()
    # run_scan(target="192.168.0.1", ports_to_scan="22,80,1900")
    tools = [
        # path_to_attacks_db,
        get_attack_types,
        get_random_attack,
        get_attack_by_description,
        get_all_attacks_by_type,
        get_attack_by_type_and_id,
        # generate_custom_attack,
        send_prompt_to_mas,
        analyze_response,
        record_attack_result,
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
                clear_report_records()
                reset_last_interaction()
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
            time_str = now.strftime("%H:%M")
            expected_n = _parse_expected_count(user_input)
            set_expected_count(expected_n)
            print(f"[!] Целевая МАС имеет url: {TARGET_MAS_URL}")
            print(f"[!] Начало тестирования  : {date_str} {time_str}")
            if check_expected_count():
                print(f"[!] Ожидается базовых атак (N): {get_expected_count()}")
            else:
                print(f"[!] Не выбрано число атак! Заполните N=...")
                continue
            problem = check_mas_available()
            if problem:
                print(f"[-] MAS недоступна, прогон не запущен: {problem}\n")
                continue

            # Запуск агента – передаём сообщение от пользователя
            time_start = timer()
            result = await send_prompt(user_input)
            elapsed_time = timer() - time_start

            # # Трейс всех сообщений хода — видно, какие инструменты реально вызывались
            # print("\n[*] Трейс хода:")
            # for msg in result["messages"]:
            #     role = msg.__class__.__name__
            #     tool_calls = getattr(msg, "tool_calls", None)
            #     if tool_calls:
            #         names = ", ".join(tc["name"] for tc in tool_calls)
            #         print(f"    [{role}] tool_calls: {names}")
            #     elif getattr(msg, "content", None):
            #         preview = str(msg.content).replace("\n", " ")[:200]
            #         print(f"    [{role}] {preview}")

            # Последнее сообщение от AI – это финальный ответ
            final_message = result["messages"][-1]
            print(f"\n[+] Время ответа: {elapsed_time:.2f} сек. Ответ агента:\n{final_message.content}\n")
        except MasUnavailableError as e:
            # История агента осталась с tool_call без ответа — сбрасываем состояние целиком.
            memory_clear()
            clear_report_records()
            reset_last_interaction()
            print(f"\n[-] Прогон прерван: MAS недоступна ({e}). Память агента и отчёт сброшены.\n")
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