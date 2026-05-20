import subprocess
import requests
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

# Конфигурация LM Studio
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
# MODEL_NAME = "qwen3.6-35b-a3b"  # Должен совпадать с загруженной моделью
MODEL_NAME = "mistral-nemo-instruct-2407"
CONFIG = {"configurable": {"thread_id": "session-1"}}
AGENT_EXEC = None

def kernel_init(tools:list):
    global MODEL_NAME
    global LM_STUDIO_BASE_URL

    llm = ChatOpenAI(
        model=MODEL_NAME,
        base_url=LM_STUDIO_BASE_URL,
        api_key="not-needed",
        # temperature=0.2,
        temperature=0.7,
    )
    
    system_prompt = """Ты — помощник для легального пентеста.
    Твои возможности:
    1. nmap_scan — сканирует порты цели и возвращает информацию о сервисах.
    2. fuzz_endpoints — ищет скрытые веб-эндпоинты методом фаззинга.

    Ты получаешь задачу от пользователя, выполняешь её с помощью инструментов и анализируешь результаты.
    При необходимости уточняй у пользователя цель и параметры.
    Всегда говори, что ты делаешь, и предупреждай, если цель не указана.
    Не выполняй атаки на отказ в обслуживании, не брутфорсь пароли и не экплуатируй найденное.
    Только информационная разведка и фаззинг."""

    memory = MemorySaver()
    global AGENT_EXEC
    AGENT_EXEC = create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
        checkpointer=memory,
    )

def send_prompt(input_str: str):
    global CONFIG
    global AGENT_EXEC
    return AGENT_EXEC.invoke(
        {"messages": [HumanMessage(content=input_str)]},
        config=CONFIG
    )
