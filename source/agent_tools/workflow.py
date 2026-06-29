from os.path import abspath
from os import makedirs
from datetime import datetime

from langchain_core.tools import tool

SAVE_PATH = "../reports"

@tool
def save_markdown_file(target: str, content: str) -> str:
    """Сохраняет текст в файл в формате Markdown."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")      # Например: 2023-10-27
    time_str = now.strftime("%H-%M")        # Например: 14-30 (используем дефис, т.к. двоеточие запрещено в Windows)

    # 4. Формируем итоговое имя файла
    file_name = f"{target}-report-{date_str}-{time_str}.md"
    file_path = abspath(SAVE_PATH) + '/' + file_name
    try:
        # Создаем директорию, если её не существует
        makedirs(abspath(SAVE_PATH), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        return f"Отчёт успешно сохранён в файл: {file_path}"
    except Exception as e:
        return f"Ошибка при сохранении файла: {str(e)}"
    
# ПРАВИЛА СОХРАНЕНИЯ ОТЧЁТА:
# Когда отчёт готов, ты ОБЯЗАН сохранить его в файл, используя инструмент `save_test_report_to_md`.
# 1. В качестве `program_name` передавай краткое название тестируемой цели/программы на английском или транслитом, без пробелов и спецсимволов (например: 'PaymentGateway', 'MobileApp_iOS').
# 2. В качестве `report_content` передавай сам текст отчёта.
# 3. НЕ ПЫТАЙСЯ сам добавлять дату и время в имя файла — инструмент сделает это автоматически.
# 4. НЕ выводи просто текст отчёта в чат, твоя главная задача — сохранить его в файл.