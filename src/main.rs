mod agent_tools;
mod config;
mod kernel;
mod llm;
mod tool;

use std::sync::Arc;
use std::time::Instant;

use chrono::Local;
use rustyline::error::ReadlineError;
use rustyline::DefaultEditor;

use crate::agent_tools::attack_generator::{
    AnalyzeResponse, GetAllAttacksByType, GetAttackByDescription, GetAttackByTypeAndId,
    GetAttackTypes, GetRandomAttack, PathToAttacksDb, SendPromptToMas,
};
use crate::agent_tools::workflow::SaveMarkdownFile;
use crate::config::Config;
use crate::kernel::kernel::Kernel;
use crate::tool::AgentTool;

#[tokio::main]
async fn main() {
    let config = match Config::load() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[-] Ошибка загрузки конфигурации: {e}");
            return;
        }
    };

    // info()
    // run_scan(target="192.168.0.1", ports_to_scan="22,80,1900")
    let tools: Vec<Box<dyn AgentTool>> = vec![
        Box::new(PathToAttacksDb::new(config.attacks_db_path.clone())),
        Box::new(GetAttackTypes::new(config.attacks_db_path.clone())),
        Box::new(GetRandomAttack::new(config.attacks_db_path.clone())),
        Box::new(GetAttackByDescription::new(config.attacks_db_path.clone())),
        Box::new(GetAllAttacksByType::new(config.attacks_db_path.clone())),
        Box::new(GetAttackByTypeAndId::new(config.attacks_db_path.clone())),
        // Box::new(GenerateCustomAttack::new(&config.base_url, &config.model)),
        Box::new(SendPromptToMas::new(&config.target_mas_url)),
        Box::new(AnalyzeResponse),
        Box::new(SaveMarkdownFile::new(config.reports_path.clone())),
    ];
    let kernel = Arc::new(Kernel::kernel_init(
        tools,
        &config.base_url,
        &config.model,
        config.system_prompt,
    ));

    let mut editor = match DefaultEditor::new() {
        Ok(e) => e,
        Err(e) => {
            eprintln!("[-] Не удалось инициализировать ввод: {e}");
            return;
        }
    };

    loop {
        let (readline_result, ed) = tokio::task::spawn_blocking(move || {
            let r = editor.readline("[>] Запрос: ");
            (r, editor)
        })
        .await
        .expect("readline task panicked");
        editor = ed;

        let user_input = match readline_result {
            Ok(line) => line.trim().to_string(),
            Err(ReadlineError::Interrupted) | Err(ReadlineError::Eof) => {
                println!("\n[!] Выход.");
                break;
            }
            Err(e) => {
                println!("\n[-] Ошибка: {e}");
                continue;
            }
        };

        if user_input.is_empty() {
            continue;
        }
        let _ = editor.add_history_entry(user_input.as_str());

        let lower = user_input.to_lowercase();
        if lower == "/exit" || lower == "/quit" {
            println!("\n[!] Выход.");
            break;
        }
        if lower == "/mem_clear" {
            kernel.memory_clear().await;
            println!("\n[!] Память агента очищена.");
            continue;
        }
        if lower == "/help" || lower == "/?" {
            println!("Выход         : '/exit' / '/quit' / Ctrl+C");
            println!("Очистка памяти: '/mem_clear'");
            println!("Справка       : '/help' / '/?'\n");
            continue;
        }

        let now = Local::now();
        println!("[!] Начало тестирования: {}", now.format("%Y-%m-%d %H:%M"));

        // Запуск агента – передаём сообщение от пользователя
        let time_start = Instant::now();
        match kernel.send_prompt(&user_input).await {
            Ok(final_message) => {
                let elapsed = time_start.elapsed();
                println!(
                    "\n[+] Время ответа: {:.2} сек. Ответ агента:\n{}\n",
                    elapsed.as_secs_f64(),
                    final_message
                );
            }
            Err(e) => {
                println!("\n[-] Ошибка: {e}");
            }
        }
    }
}
