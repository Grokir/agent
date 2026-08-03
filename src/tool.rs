use async_trait::async_trait;
use serde_json::Value;

/// Инструмент агента. Заменяет декоратор `@tool` из `langchain_core.tools`:
/// имя и JSON Schema описываются вручную (аналог автогенерации из docstring/сигнатуры).
#[async_trait]
pub trait AgentTool: Send + Sync {
    fn name(&self) -> &str;
    /// Полная схема функции в формате OpenAI function-calling:
    /// {"type": "function", "function": {"name", "description", "parameters"}}
    fn schema(&self) -> Value;
    async fn call(&self, args: Value) -> String;
}

pub fn tool_schemas(tools: &[Box<dyn AgentTool>]) -> Vec<Value> {
    tools.iter().map(|t| t.schema()).collect()
}
