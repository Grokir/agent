use anyhow::{Context, Result};
use serde::Deserialize;

const CONFIG_PATH: &str = "config.toml";

/// Настройки агента, вынесенные из кода: URL LLM, имя модели, системный промпт,
/// путь до БД атак, URL целевой MAS и директория для отчётов.
#[derive(Debug, Deserialize)]
pub struct Config {
    pub base_url: String,
    pub model: String,
    pub system_prompt: String,
    pub attacks_db_path: String,
    pub target_mas_url: String,
    pub reports_path: String,
}

impl Config {
    pub fn load() -> Result<Self> {
        let data = std::fs::read_to_string(CONFIG_PATH)
            .with_context(|| format!("не удалось прочитать {CONFIG_PATH}"))?;
        toml::from_str(&data).with_context(|| format!("не удалось разобрать {CONFIG_PATH}"))
    }
}
