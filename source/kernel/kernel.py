import subprocess
import requests
import os
from typing                         import Optional

from langchain_openai               import ChatOpenAI
from langchain_core.tools           import tool
from langchain_core.messages        import SystemMessage, HumanMessage
from langchain.agents               import create_agent
from langgraph.checkpoint.memory    import MemorySaver
from langchain.agents.middleware    import ContextEditingMiddleware, ClearToolUsesEdit

from kernel.system_prompt           import SYSPROMPT

# Конфигурация LM Studio
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
# MODEL_NAME = "qwen3.6-35b-a3b"  # Должен совпадать с загруженной моделью
# MODEL_NAME = "mistral-nemo-instruct-2407"
# MODEL_NAME = "qwen2.5-7b-instruct"
# MODEL_NAME = "qwen_qwen3.5-2b"
# MODEL_NAME = "gigachat3.1-10b-a1.8b"

# MODEL_NAME = "vulnllm-r-7b"

## OWN study
#MODEL_NAME = "qwen3-4b-diploma"
# MODEL_NAME = "cotype-2b-dataset-2.3k"
MODEL_NAME = "qwen3-4b-dataset-2.3k"
MODEL_NAME = "qwen2-3b-dataset-2.3k"
MODEL_NAME = "qwen2.5-3b-instruct"
MODEL_NAME = "qwen3-reasoning"
#MODEL_NAME = "cotype-2b-reasoning"


# UNCENSORED MODELS
# MODEL_NAME = "qwen2.5-7b-instruct-uncensored"
# MODEL_NAME = "gigachat3.1-lightning-uncensored"

# CONFIG = {"configurable": {"thread_id": "session-1"}, "recursion_limit": 200}
# CONFIG = {"configurable": {"thread_id": "session-1"}, "recursion_limit": 100} # для Cotype-2b
CONFIG = {"configurable": {"thread_id": "session-1"}, "recursion_limit": 240}    # для Qwen3
AGENT_EXEC = None
AGENT_MEMORY = None

def kernel_init(tools:list):
    global MODEL_NAME
    global LM_STUDIO_BASE_URL

    llm = ChatOpenAI(
        model=MODEL_NAME,
        base_url=LM_STUDIO_BASE_URL,
        api_key="not-needed",
        # temperature=0.1,
        # temperature=0, # для модели поведения "выбор атак"
        temperature=0.7, # для модели поведения "выбрать, отправить, мутировать, если нужно"
    )

    global AGENT_MEMORY
    AGENT_MEMORY = MemorySaver()

    global AGENT_EXEC
    AGENT_EXEC = create_agent(
        llm,
        tools,
        system_prompt=SYSPROMPT,
        checkpointer=AGENT_MEMORY,
        middleware=[ContextEditingMiddleware(
            edits=[ClearToolUsesEdit(
                # trigger=8000,          # когда токенов в истории > порога
                # keep=2,                # оставить 2 последних tool-результата
                trigger=5000,          # когда токенов в истории > порога
                keep=1,                # оставить 1 последних tool-результата
                clear_tool_inputs=True,
                placeholder="[очищено для экономии контекста]",
            )],
        )],
    )

async def send_prompt(input_str: str, role:str="user"):
    global CONFIG
    global AGENT_EXEC
    return await AGENT_EXEC.ainvoke(
        {"role": role, "messages": [HumanMessage(content=input_str)]},
        config=CONFIG
    )

async def stream_prompt(input_str: str, role:str="user"):
    """То же, что send_prompt, но отдаёт сообщения по мере выполнения графа (для TUI)."""
    global CONFIG
    global AGENT_EXEC
    async for update in AGENT_EXEC.astream(
        {"role": role, "messages": [HumanMessage(content=input_str)]},
        config=CONFIG,
        stream_mode="updates",
    ):
        for node_update in update.values():
            if not isinstance(node_update, dict):
                continue
            for msg in node_update.get("messages", []) or []:
                yield msg

def memory_clear():
    global CONFIG
    global AGENT_EXEC
    AGENT_EXEC.update_state(CONFIG, {"messages": []}) 
    
