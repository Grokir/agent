use anyhow::{bail, Result};
use serde_json::Value;
use tokio::sync::Mutex;

use crate::llm::{ChatMessage, LlmClient};
use crate::tool::{tool_schemas, AgentTool};

/// Защита от зацикливания agent-loop'а (аналог дефолтного recursion_limit в LangGraph).
const MAX_TOOL_ITERATIONS: usize = 25;

/// Заменяет связку `create_agent` + `MemorySaver` из LangChain/LangGraph:
/// хранит инструменты, LLM-клиент, системный промпт и историю сообщений одной сессии.
pub struct Kernel {
    llm: LlmClient,
    tools: Vec<Box<dyn AgentTool>>,
    tool_schemas: Vec<Value>,
    system_prompt: String,
    history: Mutex<Vec<ChatMessage>>,
}

impl Kernel {
    pub fn kernel_init(tools: Vec<Box<dyn AgentTool>>, base_url: &str, model: &str, system_prompt: String) -> Self {
        let llm = LlmClient::new(base_url, model);
        let tool_schemas = tool_schemas(&tools);
        Self {
            llm,
            tools,
            tool_schemas,
            system_prompt,
            history: Mutex::new(Vec::new()),
        }
    }

    pub async fn send_prompt(&self, input_str: &str) -> Result<String> {
        let mut history = self.history.lock().await;
        history.push(ChatMessage::user(input_str));

        for _ in 0..MAX_TOOL_ITERATIONS {
            let mut messages = Vec::with_capacity(history.len() + 1);
            messages.push(ChatMessage::system(&self.system_prompt));
            messages.extend(history.iter().cloned());

            let assistant_msg = self.llm.chat(&messages, &self.tool_schemas, 0.0).await?;

            let tool_calls = assistant_msg.tool_calls.clone();
            history.push(assistant_msg.clone());

            match tool_calls {
                Some(calls) if !calls.is_empty() => {
                    for call in calls {
                        let result = self.execute_tool(&call.function.name, &call.function.arguments).await;
                        history.push(ChatMessage::tool_result(&call.id, result));
                    }
                }
                _ => {
                    return Ok(assistant_msg.content.unwrap_or_default());
                }
            }
        }

        bail!("Превышено максимальное число итераций agent-loop'а ({MAX_TOOL_ITERATIONS})")
    }

    async fn execute_tool(&self, name: &str, raw_arguments: &str) -> String {
        let Some(tool) = self.tools.iter().find(|t| t.name() == name) else {
            return format!("Ошибка: инструмент '{name}' не найден");
        };

        let args: Value = serde_json::from_str(raw_arguments).unwrap_or(Value::Null);
        tool.call(args).await
    }

    pub async fn memory_clear(&self) {
        self.history.lock().await.clear();
    }
}
