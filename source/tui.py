# Отключение предупреждений от Pydantic об версии Python (как в main.py)
import warnings

warnings.filterwarnings("ignore")
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None


import asyncio
from time import perf_counter as timer
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage
from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Markdown, RichLog, Static

from kernel.kernel import MODEL_NAME, kernel_init, stream_prompt, memory_clear
from agent_tools.attack_generator import (
    TARGET_MAS_URL,
    get_attack_types,
    get_random_attack,
    get_attack_by_description,
    get_all_attacks_by_type,
    get_attack_by_type_and_id,
    send_prompt_to_mas,
    analyze_response,
    reset_last_interaction,
    set_confirm_send_hook,
    set_mas_error_hook,
    check_mas_available,
    MasUnavailableError,
)
from agent_tools.workflow import (
    save_markdown_file,
    record_attack_result,
    clear_report_records,
    set_expected_count,
    get_expected_count,
    check_expected_count,
    get_records,
)
from main import _parse_expected_count

TOOLS = [
    get_attack_types,
    get_random_attack,
    get_attack_by_description,
    get_all_attacks_by_type,
    get_attack_by_type_and_id,
    send_prompt_to_mas,
    analyze_response,
    record_attack_result,
    save_markdown_file,
]

HELP_TEXT = (
    "**Команды**\n\n"
    "- `tag=...; N=5` — запуск тестирования (N обязателен)\n"
    "- `/mem_clear` — очистка памяти агента и отчёта\n"
    "- `/help`, `/?` — справка\n"
    "- `/exit`, `/quit`, `Ctrl+Q` — выход\n"
    "- `Esc` — прервать текущий прогон\n"
    "- `Ctrl+T` — вкл/выкл подтверждение отправки запросов в MAS\n\n"
    "Перед каждой отправкой в MAS спрашивается подтверждение: "
    "`Y` — отправить, `N` — отклонить, `A` — отправить и дальше без вопросов.\n"
)

PREVIEW_LEN = 300


def _preview(text: str) -> str:
    text = str(text).replace("\n", " ")
    return text if len(text) <= PREVIEW_LEN else text[:PREVIEW_LEN] + "…"


class ConfirmSendScreen(ModalScreen[str]):
    """Подтверждение отправки запроса в MAS: возвращает "yes" / "no" / "all"."""

    CSS = """
    ConfirmSendScreen { align: center middle; }
    #dialog { width: 90%; max-width: 120; height: auto; max-height: 80%;
              border: thick $warning; background: $surface; padding: 1 2; }
    #payload { height: auto; max-height: 20; border: round $primary; margin: 1 0; }
    #buttons { height: auto; align: center middle; }
    #buttons Button { margin: 0 1; }
    """

    BINDINGS = [
        Binding("y", "choose('yes')", "Да"),
        Binding("n,escape", "choose('no')", "Нет"),
        Binding("a", "choose('all')", "Все (авто)"),
    ]

    def __init__(self, prompt: str, session_id: str) -> None:
        super().__init__()
        self._prompt = prompt
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[b]Отправить запрос в MAS?[/]")
            yield Label(f"[dim]URL: {escape(TARGET_MAS_URL)}  │  session_id: {escape(self._session_id)}[/]")
            with VerticalScroll(id="payload"):
                yield Static(self._prompt, markup=False)
            with Horizontal(id="buttons"):
                yield Button("Да (Y)", id="yes", variant="success")
                yield Button("Нет (N)", id="no", variant="error")
                yield Button("Все — авто (A)", id="all", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)

    def action_choose(self, choice: str) -> None:
        self.dismiss(choice)


class MasErrorScreen(ModalScreen[str]):
    """MAS недоступна: возвращает "retry" / "skip" / "abort"."""

    CSS = """
    MasErrorScreen { align: center middle; }
    #dialog { width: 90%; max-width: 120; height: auto; max-height: 80%;
              border: thick $error; background: $surface; padding: 1 2; }
    #reason { height: auto; max-height: 12; border: round $error; margin: 1 0; }
    #buttons { height: auto; align: center middle; }
    #buttons Button { margin: 0 1; }
    """

    BINDINGS = [
        Binding("r", "choose('retry')", "Повторить"),
        Binding("s", "choose('skip')", "Пропустить"),
        Binding("a,escape", "choose('abort')", "Прервать"),
    ]

    def __init__(self, reason: str) -> None:
        super().__init__()
        self._reason = reason

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[b]MAS недоступна[/] (повторы не помогли)")
            with VerticalScroll(id="reason"):
                yield Static(self._reason, markup=False)
            yield Label(
                "[dim]Пропустить — модель перейдёт к следующей атаке; "
                "Прервать — остановить прогон и сбросить состояние.[/]"
            )
            with Horizontal(id="buttons"):
                yield Button("Повторить (R)", id="retry", variant="primary")
                yield Button("Пропустить (S)", id="skip", variant="warning")
                yield Button("Прервать (A)", id="abort", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)

    def action_choose(self, choice: str) -> None:
        self.dismiss(choice)


class AgentTUI(App):
    TITLE = "Red-team агент MAS"

    CSS = """
    #status { height: 1; padding: 0 1; background: $boost; }
    #main { height: 1fr; }
    #trace { width: 3fr; border: round $primary; }
    #attacks { width: 2fr; border: round $secondary; }
    #answer-box { height: auto; max-height: 12; border: round $accent; }
    #answer { margin: 0; padding: 0 1; }
    #answer > * { margin: 0; }
    #prompt { dock: bottom; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Выход"),
        Binding("escape", "cancel_run", "Прервать прогон"),
        Binding("ctrl+l", "clear_trace", "Очистить лог"),
        Binding("ctrl+t", "toggle_auto_send", "Подтверждение вкл/выкл"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._agent_running = False
        # True — отправка в MAS без подтверждения (выбран "All" или Ctrl+T).
        self._auto_send = False
        # Открытый диалог оператора: (future ответа, ответ по умолчанию при прерывании).
        self._pending_dialog: "tuple[asyncio.Future, str] | None" = None
        # Приложение закрывается — виджеты уже сняты, обновлять UI из воркера нельзя.
        self._closing = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status")
        with Horizontal(id="main"):
            yield RichLog(id="trace", wrap=True, markup=True, highlight=False)
            yield DataTable(id="attacks", zebra_stripes=True, cursor_type="row")
        with VerticalScroll(id="answer-box"):
            yield Markdown(HELP_TEXT, id="answer")
        yield Input(placeholder="[>] Запрос: tag=...; N=5", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#trace").border_title = "Ход агента"
        self.query_one("#attacks").border_title = "Записанные атаки"
        self.query_one("#answer-box").border_title = "Ответ агента"
        table = self.query_one("#attacks", DataTable)
        table.add_columns("ID", "Тип", "Подрядчик", "Вердикт")
        kernel_init(tools=TOOLS)
        set_confirm_send_hook(self._confirm_send)
        set_mas_error_hook(self._on_mas_error)
        self._refresh_status()
        self.query_one("#prompt", Input).focus()

    # ---------- отображение ----------

    def _log(self, text: str) -> None:
        self.query_one("#trace", RichLog).write(text)

    def _refresh_status(self) -> None:
        n = get_expected_count()
        done = len(get_records())
        progress = f"{done}/{n}" if n else f"{done}/—"
        state = "[b yellow]выполняется[/]" if self._agent_running else "[b green]ожидание[/]"
        self.query_one("#status", Static).update(
            f"MAS: {escape(TARGET_MAS_URL)}  │  модель: {escape(MODEL_NAME)}  │  "
            f"атак: {progress}  │  {state}  │  "
            + ("[b red]отправка: авто[/]" if self._auto_send else "[b]отправка: с подтверждением[/]")
        )

    def _refresh_attacks(self) -> None:
        table = self.query_one("#attacks", DataTable)
        table.clear()
        for r in get_records():
            table.add_row(
                str(r["attack_id"]), r["attack_type"], r["target_agent"] or "—", r["verdict"]
            )

    def _show_message(self, msg) -> None:
        if self._closing:
            return
        if isinstance(msg, AIMessage):
            for tc in msg.tool_calls or []:
                args = ", ".join(f"{k}={v!r}" for k, v in tc["args"].items())
                self._log(f"[cyan]→ {escape(tc['name'])}[/]({escape(_preview(args))})")
            if not msg.tool_calls and msg.content:
                self._log(f"[magenta]◆ ответ модели:[/] {escape(_preview(msg.content))}")
        elif isinstance(msg, ToolMessage):
            color = "red" if str(msg.content).startswith(("ОТКЛОНЕНО", "Ошибка")) else "green"
            self._log(f"[{color}]← {escape(msg.name or '?')}:[/] {escape(_preview(msg.content))}")
            if msg.name == "record_attack_result":
                self._refresh_attacks()
                self._refresh_status()

    # ---------- подтверждение отправки в MAS ----------

    def _confirm_send(self, prompt: str, session_id: str) -> bool:
        """Хук для send_prompt_to_mas. Вызывается из потока инструмента и блокирует его до ответа."""
        if self._auto_send:
            return True
        return self.call_from_thread(self._ask_confirm, prompt, session_id)

    async def _ask_dialog(self, screen: ModalScreen, default: str) -> str:
        """Показывает диалог и ждёт выбора оператора (default — если диалог снят прерыванием)."""
        fut = asyncio.get_running_loop().create_future()
        self._pending_dialog = (fut, default)

        def on_choice(choice: "str | None") -> None:
            if not fut.done():
                fut.set_result(choice or default)

        self.push_screen(screen, callback=on_choice)
        try:
            return await fut
        finally:
            self._pending_dialog = None

    async def _ask_confirm(self, prompt: str, session_id: str) -> bool:
        choice = await self._ask_dialog(ConfirmSendScreen(prompt, session_id), "no")
        if choice == "all":
            self._auto_send = True
            self._refresh_status()
            self._log("[yellow]✔ отправка подтверждена, дальше — без подтверждения (авто)[/]")
        elif choice == "yes":
            self._log("[green]✔ отправка подтверждена оператором[/]")
        else:
            self._log("[red]✖ отправка отклонена оператором[/]")
        return choice in ("yes", "all")

    def _on_mas_error(self, reason: str) -> str:
        """Хук для send_prompt_to_mas при недоступности MAS. Вызывается из потока инструмента."""
        return self.call_from_thread(self._ask_mas_error, reason)

    async def _ask_mas_error(self, reason: str) -> str:
        self._log(f"[b red]✖ MAS недоступна:[/] {escape(reason)}")
        choice = await self._ask_dialog(MasErrorScreen(reason), "abort")
        labels = {"retry": "повтор отправки", "skip": "атака пропущена", "abort": "прогон прерывается"}
        self._log(f"[yellow]↳ решение оператора: {labels.get(choice, choice)}[/]")
        return choice

    def _drop_pending_dialog(self) -> None:
        """Снимает открытый диалог ответом по умолчанию, чтобы не повис поток инструмента."""
        if self._pending_dialog is not None:
            fut, default = self._pending_dialog
            if not fut.done():
                fut.set_result(default)
            if self.screen_stack and isinstance(self.screen_stack[-1], (ConfirmSendScreen, MasErrorScreen)):
                self.pop_screen()

    def action_toggle_auto_send(self) -> None:
        self._auto_send = not self._auto_send
        self._refresh_status()
        self.notify("Отправка в MAS: " + ("авто" if self._auto_send else "с подтверждением"))

    def on_unmount(self) -> None:
        self._closing = True
        self._drop_pending_dialog()
        self.workers.cancel_group(self, "agent")

    # ---------- ввод ----------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        event.input.value = ""
        if not user_input:
            return
        cmd = user_input.lower()
        if cmd in ("/exit", "/quit"):
            self.exit()
            return
        if cmd in ("/help", "/?"):
            self.query_one("#answer", Markdown).update(HELP_TEXT)
            return
        if self._agent_running:
            self.notify("Прогон уже идёт. Esc — прервать.", severity="warning")
            return
        if cmd == "/mem_clear":
            self._reset_state()
            self.notify("Память агента очищена.")
            return

        set_expected_count(_parse_expected_count(user_input))
        if not check_expected_count():
            self.notify("Не выбрано число атак! Заполните N=...", severity="error")
            return
        self.run_agent(user_input)

    def _abort_run_state(self, message: str) -> None:
        # История графа может остаться с tool_call без ответа инструмента — такую историю
        # модель не примет, поэтому после прерывания сбрасываем всё состояние целиком.
        self._reset_state()
        self._log(f"[b red]■ {message}, память агента и отчёт сброшены.[/]")

    def _reset_state(self) -> None:
        memory_clear()
        clear_report_records()
        reset_last_interaction()
        self._refresh_attacks()
        self._refresh_status()

    # ---------- прогон ----------

    @work(exclusive=True, group="agent")
    async def run_agent(self, user_input: str) -> None:
        prompt = self.query_one("#prompt", Input)
        answer = self.query_one("#answer", Markdown)
        self._agent_running = True
        prompt.disabled = True
        self._refresh_status()
        self._log(
            f"\n[b]▶ Начало тестирования {datetime.now():%Y-%m-%d %H:%M}, "
            f"N={get_expected_count()}[/]\n[dim]{escape(user_input)}[/]"
        )
        await answer.update("_Проверка доступности MAS…_")
        problem = await asyncio.to_thread(check_mas_available)
        if problem:
            self._log(f"[b red]✖ MAS недоступна, прогон не запущен:[/] {escape(problem)}")
            await answer.update(f"**MAS недоступна, прогон не запущен.**\n\n{problem}")
            self._agent_running = False
            prompt.disabled = False
            prompt.focus()
            self._refresh_status()
            return
        await answer.update("_Агент работает…_")

        time_start = timer()
        final_message = None
        try:
            async for msg in stream_prompt(user_input):
                self._show_message(msg)
                if isinstance(msg, AIMessage) and not msg.tool_calls:
                    final_message = msg
            elapsed = timer() - time_start
            self._log(f"[b]■ Готово за {elapsed:.2f} сек.[/]")
            await answer.update(
                final_message.content if final_message else "_Агент не вернул финальный ответ._"
            )
        except asyncio.CancelledError:
            if self._closing:
                raise
            self._abort_run_state("Прогон прерван")
            await answer.update("_Прогон прерван._")
            raise
        except MasUnavailableError as e:
            if self._closing:
                return
            self._abort_run_state("Прогон прерван: MAS недоступна")
            await answer.update(f"**Прогон прерван: MAS недоступна.**\n\n{e}")
        except Exception as e:
            if self._closing:
                return
            self._log(f"[b red]✖ Ошибка: {escape(str(e))}[/]")
            await answer.update(f"**Ошибка:** `{e}`")
        finally:
            self._agent_running = False
            if not self._closing:
                prompt.disabled = False
                prompt.focus()
                self._refresh_attacks()
                self._refresh_status()

    def action_cancel_run(self) -> None:
        if self._agent_running:
            self._drop_pending_dialog()
            self.workers.cancel_group(self, "agent")

    def action_clear_trace(self) -> None:
        self.query_one("#trace", RichLog).clear()


if __name__ == "__main__":
    AgentTUI().run()
