//! Простой сетевой сканер на основе Nmap (учебный пример), как и в Python-версии,
//! НЕ подключён в src/main.rs как активный инструмент агента.
#![allow(dead_code)]

use std::process::Command;

use anyhow::{bail, Context, Result};
use async_trait::async_trait;
use roxmltree::Document;
use serde_json::{json, Value};

use crate::tool::AgentTool;

pub fn info() {
    println!(
        "\nПростой сетевой сканер на основе Nmap (учебный пример).\nСканирует указанный хост на наиболее распространённые порты,\nвыводит их состояние и версии сервисов.\n"
    );
}

struct PortInfo {
    port: u32,
    protocol: String,
    state: String,
    service: String,
}

struct HostScanResult {
    state: String,
    ports: Vec<PortInfo>,
}

/// Выполняет сканирование хоста с помощью Nmap.
fn scan_host(target_host: &str) -> Result<Option<HostScanResult>> {
    println!("[*] Запуск сканирования узла ({target_host})...");

    // Аргументы Nmap: -F (частые порты) -n (без DNS) -T5 (агрессивный тайминг) -A (определение ОС/версий)
    let output = Command::new("nmap")
        .args(["-F", "-n", "-T5", "-A", "-oX", "-", target_host])
        .output()
        .context("не удалось запустить nmap (проверьте, что он установлен)")?;

    if !output.status.success() {
        bail!("nmap завершился с ошибкой: {}", String::from_utf8_lossy(&output.stderr));
    }

    let xml = String::from_utf8_lossy(&output.stdout);
    let doc = Document::parse(&xml).context("не удалось разобрать XML-вывод nmap")?;

    let Some(host_node) = doc.descendants().find(|n| n.has_tag_name("host")) else {
        return Ok(None);
    };

    let state = host_node
        .descendants()
        .find(|n| n.has_tag_name("status"))
        .and_then(|n| n.attribute("state"))
        .unwrap_or("unknown")
        .to_string();

    let mut ports = Vec::new();
    for port_node in host_node.descendants().filter(|n| n.has_tag_name("port")) {
        let protocol = port_node.attribute("protocol").unwrap_or("tcp").to_string();
        let port: u32 = port_node
            .attribute("portid")
            .and_then(|v| v.parse().ok())
            .unwrap_or(0);
        let port_state = port_node
            .children()
            .find(|n| n.has_tag_name("state"))
            .and_then(|n| n.attribute("state"))
            .unwrap_or("unknown")
            .to_string();

        let service_node = port_node.children().find(|n| n.has_tag_name("service"));
        let service_name = service_node.and_then(|n| n.attribute("name")).unwrap_or("unknown");
        let product = service_node.and_then(|n| n.attribute("product")).unwrap_or("");
        let version = service_node.and_then(|n| n.attribute("version")).unwrap_or("");
        let extrainfo = service_node.and_then(|n| n.attribute("extrainfo")).unwrap_or("");

        // Собираем полную информацию о сервисе
        let mut service_full = service_name.to_string();
        if !product.is_empty() {
            service_full += &format!(" ({product}");
            if !version.is_empty() {
                service_full += &format!(" {version}");
            }
            if !extrainfo.is_empty() {
                service_full += &format!(" {extrainfo}");
            }
            service_full += ")";
        }

        ports.push(PortInfo {
            port,
            protocol,
            state: port_state,
            service: service_full,
        });
    }

    Ok(Some(HostScanResult { state, ports }))
}

fn format_scan_result(result: &HostScanResult) -> String {
    let mut out = format!("Состояние: {}", result.state.to_uppercase());
    if result.ports.is_empty() {
        out += "\nНет открытых портов";
    }
    for p in &result.ports {
        out += &format!(
            "\nПорт {}/{} {} : {}",
            p.port,
            p.protocol,
            p.state.to_uppercase(),
            p.service
        );
    }
    out
}

fn run_scan_blocking(target: &str) -> String {
    match scan_host(target) {
        Ok(None) => format!(
            "[!] Хост {target} не найден в результатах сканирования. Возможно, он недоступен или отфильтрован."
        ),
        Ok(Some(result)) => format_scan_result(&result),
        Err(e) => format!("[!] Ошибка Nmap: {e}"),
    }
}

/// Инструмент агента: запуск nmap-сканирования порта на целевом IP.
/// Как и в Python-версии — реализован, но не зарегистрирован в активном списке tools.
pub struct RunScan;

#[async_trait]
impl AgentTool for RunScan {
    fn name(&self) -> &str {
        "run_scan"
    }

    fn schema(&self) -> Value {
        json!({
            "type": "function",
            "function": {
                "name": "run_scan",
                "description": "Run nmap port scan on a target IP with specified ports.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "IP-адрес или доменное имя цели"}
                    }
                }
            }
        })
    }

    async fn call(&self, args: Value) -> String {
        let target = args
            .get("target")
            .and_then(Value::as_str)
            .unwrap_or("127.0.0.1")
            .to_string();

        tokio::task::spawn_blocking(move || run_scan_blocking(&target))
            .await
            .unwrap_or_else(|e| format!("[!] Непредвиденная ошибка: {e}"))
    }
}

/// Тест флагов nmap для локального запуска без агента (как `run()` в Python-версии).
pub fn run(target: &str) -> String {
    match scan_host(target) {
        Ok(None) => {
            let s = format!(
                "[!] Хост {target} не найден в результатах сканирования. Возможно, он недоступен или отфильтрован."
            );
            println!("{s}");
            s
        }
        Ok(Some(result)) => {
            let s = format_scan_result(&result);
            println!("{s}");
            s
        }
        Err(e) => {
            let s = format!("[!] Ошибка Nmap: {e}");
            println!("{s}");
            s
        }
    }
}
