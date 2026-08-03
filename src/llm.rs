use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Одно сообщение диалога в формате, совместимом с OpenAI Chat Completions API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<ToolCall>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

impl ChatMessage {
    pub fn system(content: &str) -> Self {
        Self {
            role: "system".to_string(),
            content: Some(content.to_string()),
            tool_calls: None,
            tool_call_id: None,
            name: None,
        }
    }

    pub fn user(content: &str) -> Self {
        Self {
            role: "user".to_string(),
            content: Some(content.to_string()),
            tool_calls: None,
            tool_call_id: None,
            name: None,
        }
    }

    pub fn tool_result(tool_call_id: &str, content: String) -> Self {
        Self {
            role: "tool".to_string(),
            content: Some(content),
            tool_calls: None,
            tool_call_id: Some(tool_call_id.to_string()),
            name: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: String,
    #[serde(rename = "type")]
    pub kind: String,
    pub function: FunctionCall,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionCall {
    pub name: String,
    pub arguments: String,
}

#[derive(Serialize)]
struct ChatCompletionRequest<'a> {
    model: &'a str,
    messages: &'a [ChatMessage],
    #[serde(skip_serializing_if = "Option::is_none")]
    tools: Option<&'a [Value]>,
    temperature: f32,
}

#[derive(Deserialize)]
struct ChatCompletionResponse {
    choices: Vec<Choice>,
}

#[derive(Deserialize)]
struct Choice {
    message: ChatMessage,
}

/// Клиент для OpenAI-совместимого чат-эндпоинта (LM Studio и т.п.).
/// Заменяет `langchain_openai.ChatOpenAI` из Python-версии.
pub struct LlmClient {
    http: reqwest::Client,
    base_url: String,
    model: String,
}

impl LlmClient {
    pub fn new(base_url: impl Into<String>, model: impl Into<String>) -> Self {
        Self {
            http: reqwest::Client::new(),
            base_url: base_url.into(),
            model: model.into(),
        }
    }

    pub async fn chat(
        &self,
        messages: &[ChatMessage],
        tools: &[Value],
        temperature: f32,
    ) -> Result<ChatMessage> {
        let url = format!("{}/chat/completions", self.base_url.trim_end_matches('/'));
        let body = ChatCompletionRequest {
            model: &self.model,
            messages,
            tools: if tools.is_empty() { None } else { Some(tools) },
            temperature,
        };

        let resp = self
            .http
            .post(&url)
            .json(&body)
            .send()
            .await
            .context("Ошибка при обращении к LLM")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            bail!("LLM вернул ошибку {status}: {text}");
        }

        let parsed: ChatCompletionResponse = resp
            .json()
            .await
            .context("Не удалось разобрать ответ LLM")?;

        let choice = parsed
            .choices
            .into_iter()
            .next()
            .context("LLM вернул пустой список choices")?;

        Ok(choice.message)
    }
}
