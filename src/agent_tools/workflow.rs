use async_trait::async_trait;
use chrono::Local;
use serde_json::{json, Value};

use crate::tool::AgentTool;

pub struct SaveMarkdownFile {
    path: String,
}

impl SaveMarkdownFile {
    pub fn new(path: String) -> Self {
        Self { path }
    }
}

#[async_trait]
impl AgentTool for SaveMarkdownFile {
    fn name(&self) -> &str {
        "save_markdown_file"
    }

    fn schema(&self) -> Value {
        json!({
            "type": "function",
            "function": {
                "name": "save_markdown_file",
                "description": "Сохраняет текст в файл в формате Markdown.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Метка тестируемой цели, используется как имя файла отчёта"},
                        "content": {"type": "string", "description": "Содержание отчёта"}
                    },
                    "required": ["target", "content"]
                }
            }
        })
    }

    async fn call(&self, args: Value) -> String {
        let target = args.get("target").and_then(Value::as_str).unwrap_or_default();
        let content = args.get("content").and_then(Value::as_str).unwrap_or_default();

        let now = Local::now();
        let date_str = now.format("%Y-%m-%d");
        let time_str = now.format("%H-%M"); // используем дефис, т.к. двоеточие запрещено в Windows

        let file_name = format!("{target}-report--{date_str}--{time_str}.md");

        let save_dir = match std::path::absolute(&self.path) {
            Ok(p) => p,
            Err(e) => return format!("Ошибка при сохранении файла: {e}"),
        };
        let file_path = save_dir.join(&file_name);

        if let Err(e) = std::fs::create_dir_all(&save_dir) {
            return format!("Ошибка при сохранении файла: {e}");
        }

        match std::fs::write(&file_path, content) {
            Ok(()) => format!("Отчёт успешно сохранён в файл: {}", file_path.display()),
            Err(e) => format!("Ошибка при сохранении файла: {e}"),
        }
    }
}
