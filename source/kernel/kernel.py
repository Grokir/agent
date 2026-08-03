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
# MODEL_NAME = "mistral-nemo-instruct-2407"
# MODEL_NAME = "qwen2.5-7b-instruct"
MODEL_NAME = "qwen2.5-3b-instruct"
# MODEL_NAME = "qwen_qwen3.5-2b"
# MODEL_NAME = "gigachat3.1-10b-a1.8b"

# UNCENSORED MODELS
# MODEL_NAME = "qwen2.5-7b-instruct-uncensored"
# MODEL_NAME = "gigachat3.1-lightning-uncensored"

CONFIG = {"configurable": {"thread_id": "session-1"}}
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
        temperature=0,
    )

    global AGENT_MEMORY
    AGENT_MEMORY = MemorySaver()

    global AGENT_EXEC
    AGENT_EXEC = create_agent(
        llm,
        tools,
        system_prompt=SYSPROMPT,
        checkpointer=AGENT_MEMORY,
    )

async def send_prompt(input_str: str, role:str="user"):
    global CONFIG
    global AGENT_EXEC
    return await AGENT_EXEC.ainvoke(
        {"role": role, "messages": [HumanMessage(content=input_str)]},
        config=CONFIG
    )

def memory_clear():
    global CONFIG
    global AGENT_EXEC
    AGENT_EXEC.update_state(CONFIG, {"messages": []}) 
    