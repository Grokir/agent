import subprocess
import requests
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from kernel.system_prompt import SYSPROMPT

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

    memory = MemorySaver()
    global AGENT_EXEC
    AGENT_EXEC = create_agent(
        llm,
        tools,
        system_prompt=SYSPROMPT,
        checkpointer=memory,
    )

def send_prompt(input_str: str, role:str="system"):
    global CONFIG
    global AGENT_EXEC
    return AGENT_EXEC.invoke(
        {"role": role, "messages": [HumanMessage(content=input_str)]},
        config=CONFIG
    )