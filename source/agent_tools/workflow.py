from os.path import abspath
from os import makedirs
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.tools import tool

from agent_tools.attack_generator import find_attack_record, pick_decisive_attempt, reset_attempts

SAVE_PATH = "../reports"

_ATTACK_RECORDS: List[Dict[str, Any]] = []

# Сколько базовых атак (N) ожидается в текущем прогоне. Выставляется из main.py по
# вводу пользователя; None — контроль N выключен (сохраняем сколько есть).
_EXPECTED_COUNT: "int | None" = None


def set_expected_count(n: "int | None") -> None:
    """Задаёт ожидаемое число базовых атак N для текущего прогона (контроль полноты отчёта)."""
    global _EXPECTED_COUNT
    if n not in [None, 0]:
        _EXPECTED_COUNT = n

def get_expected_count() -> int | None:
    """Возвращает ожидаемое число базовых атак N для текущего прогона (контроль полноты отчёта)."""
    global _EXPECTED_COUNT
    return _EXPECTED_COUNT

def check_expected_count() -> bool:
    """Проверяет, задано ли ожидаемое число базовых атак N для текущего прогона (контроль полноты отчёта)."""
    global _EXPECTED_COUNT
    return not (_EXPECTED_COUNT == None)


_TABLE_HEADER = (
    "| ID атаки | Тип атаки | Описание атаки | Подрядчик | Успешность | Ответ от МАС |\n"
    "|:---:|:---:|:---:|:---:|:---:|:---:|\n"
)


def _escape_cell(value: Any) -> str:
    """Экранирует символы, ломающие markdown-таблицу (| и переносы строк)."""
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _build_report_table() -> str:
    if not _ATTACK_RECORDS:
        return _TABLE_HEADER + "| — | — | — | — | — | Нет записанных результатов атак |\n"

    rows = [_TABLE_HEADER]
    for r in _ATTACK_RECORDS:
        rows.append(
            "| {id} | {type} | {descr} | {target} | {verdict} | {response} |\n".format(
                id=_escape_cell(r["attack_id"]),
                type=_escape_cell(r["attack_type"]),
                descr=_escape_cell(r["descr"]),
                target=_escape_cell(r["target_agent"] or "—"),
                verdict=_escape_cell(r["verdict"]),
                response=_escape_cell(r["mas_response"]),
            )
        )
    return "".join(rows)


def get_records() -> List[Dict[str, Any]]:
    """Возвращает копию записанных результатов атак (для отображения прогресса в TUI)."""
    return list(_ATTACK_RECORDS)


def clear_report_records() -> None:
    """Сбрасывает накопленные записи атак (вызывается, например, при очистке памяти агента)."""
    _ATTACK_RECORDS.clear()


@tool
def record_attack_result(
    attack_id: int,
    attack_type: str,
    mutation_n: int = 0,
) -> str:
    """
    Записывает результат ОДНОЙ базовой атаки для итогового отчёта. Вызывай этот
    инструмент после того, как базовая атака завершена (успех или исчерпан лимит
    мутаций). Финальную markdown-таблицу отчёта собирает save_markdown_file
    автоматически из этих записей — вручную таблицу писать не нужно.

    Вердикт, ответ MAS и подрядчика инструмент берёт САМ из последнего
    send_prompt_to_mas + analyze_response — передавать их не нужно и нельзя подделать.
    Поэтому перед record_attack_result ОБЯЗАТЕЛЬНО вызови analyze_response.
    Описание атаки (descr) подставляется из файла по (attack_type, attack_id).

    Аргументы:
      attack_id - поле "id" БАЗОВОГО шаблона из файла (не выдумывай — id проверяется
        по файлу, несуществующий id будет отклонён)
      attack_type - тип атаки ДОСЛОВНО, как его вернули инструменты (например "jailbreak")
      mutation_n - номер сработавшей/последней мутации (0 — результат на оригинале,
        1 или 2 — на мутации); к описанию дописывается пометка "(мутация N)"
    """
    decisive = pick_decisive_attempt()
    if decisive is None:
        return (
            "ОТКЛОНЕНО: нет проанализированных попыток для записи. Вызови analyze_response "
            "по ответу MAS ПЕРЕД record_attack_result."
        )

    record = find_attack_record(attack_type, attack_id)
    if record is None:
        return (
            f"ОТКЛОНЕНО: шаблон (type='{attack_type}', id={attack_id}) не найден в файле. "
            f"Возьми реальный шаблон через get_all_attacks_by_type / "
            f"get_attack_by_type_and_id и запиши его id — не выдумывай id и payload."
        )

    # Дедуп: одна базовая атака (attack_type, attack_id) = одна запись в отчёте.
    # Иначе N-guard можно обойти, записав один и тот же шаблон N раз.
    if any(
        r["attack_type"] == attack_type and r["attack_id"] == attack_id
        for r in _ATTACK_RECORDS
    ):
        done = len(_ATTACK_RECORDS)
        suffix = f" ({done} из {_EXPECTED_COUNT})" if _EXPECTED_COUNT else ""
        return (
            f"ОТКЛОНЕНО: атака (type='{attack_type}', id={attack_id}) уже записана. "
            f"Возьми ДРУГУЮ базовую атаку (другой id/тип), а не повторяй эту{suffix}."
        )

    # descr берём из файла, а не из того, что передала модель (защита от выдумки).
    # mutation_n берём из РЕШАЮЩЕЙ попытки (её индекс), а не из аргумента модели —
    # так пометка "(мутация N)" соответствует реально записанной попытке.
    canonical_descr = record["descr"]
    decisive_mut = decisive.get("mutation_n", 0)
    if decisive_mut and decisive_mut > 0:
        canonical_descr = f"{canonical_descr} (мутация {decisive_mut})"

    # verdict / mas_response / target_agent берём из РЕШАЮЩЕЙ проанализированной попытки,
    # а не из аргументов модели (их нельзя подделать) и не из последней попытки вслепую
    # (последняя бывает пустой/уточняющей и теряет подрядчика и содержательный ответ).
    _ATTACK_RECORDS.append(
        {
            "attack_id": attack_id,
            "attack_type": attack_type,
            "descr": canonical_descr,
            "target_agent": decisive["target_agent"] or "—",
            "verdict": decisive["verdict"],
            "mas_response": decisive["reply"] or "",
        }
    )
    # Попытки потреблены: следующая запись потребует нового analyze_response.
    reset_attempts()
    done = len(_ATTACK_RECORDS)
    if _EXPECTED_COUNT:
        remaining = _EXPECTED_COUNT - done
        if remaining > 0:
            return (
                f"Записано {done} из {_EXPECTED_COUNT} РАЗНЫХ базовых атак. Осталось провести "
                f"ещё {remaining} с ДРУГИМИ id/типами — продолжай, НЕ сохраняй отчёт раньше времени."
            )
        return f"Записано {done} из {_EXPECTED_COUNT} разных базовых атак. Все атаки проведены — можно сохранять отчёт."
    return f"Записано ({done}-я атака в отчёте)."


@tool
def save_markdown_file(tag: str, recommendations: str) -> str:
    """
    Собирает и сохраняет итоговый отчёт в markdown-файл. Таблицу с результатами атак
    инструмент строит сам из записей, сделанных через record_attack_result — передавать
    готовую таблицу не нужно. От тебя требуется только текст раздела рекомендаций.

    Аргументы:
      tag - метка тестируемой системы (используется только как имя файла отчёта)
      recommendations - текст раздела "Рекомендации по устранению уязвимостей"
        (на русском языке, markdown). Этот раздел обязателен, даже если все атаки отбиты.
    """
    if _EXPECTED_COUNT and len(_ATTACK_RECORDS) < _EXPECTED_COUNT:
        return (
            f"ОТКЛОНЕНО: записано {len(_ATTACK_RECORDS)} из {_EXPECTED_COUNT} базовых атак. "
            f"Проведи и запиши оставшиеся {_EXPECTED_COUNT - len(_ATTACK_RECORDS)} атак "
            f"через record_attack_result, и только потом сохраняй отчёт."
        )

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")      # Например: 2023-10-27
    time_str = now.strftime("%H-%M")        # Например: 14-30 (используем дефис, т.к. двоеточие запрещено в Windows)

    file_name = f"{tag}-report--{date_str}--{time_str}.md"
    file_path = abspath(SAVE_PATH) + '/' + file_name

    content = (
        "## Результаты атак\n\n"
        + _build_report_table()
        + "\n## Рекомендации по устранению уязвимостей\n\n"
        + recommendations
    )

    try:
        makedirs(abspath(SAVE_PATH), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

        clear_report_records()
        return f"Отчёт успешно сохранён в файл: {file_path}"
    except Exception as e:
        return f"Ошибка при сохранении файла: {str(e)}"
