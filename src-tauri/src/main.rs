// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::ShellExt;

/// Estado compartido del servidor backend
struct BackendServer {
    child: Arc<Mutex<Option<Child>>>,
}

impl BackendServer {
    fn new() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
        }
    }
}

/// Inicia el servidor backend como sidecar
#[tauri::command]
async fn start_backend_server(
    app: AppHandle,
    server_state: State<'_, BackendServer>,
) -> Result<String, String> {
    let mut child_lock = server_state.child.lock().unwrap();

    // Si ya está corriendo, no hacer nada
    if child_lock.is_some() {
        return Ok("Backend server already running".to_string());
    }

    // Obtener el comando del sidecar
    let sidecar_command = app
        .shell()
        .sidecar("narrative-assistant-server")
        .map_err(|e| format!("Failed to get sidecar command: {}", e))?;

    // Ejecutar el sidecar
    let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    // Guardar el proceso hijo
    *child_lock = Some(child);

    // Spawn una tarea para leer la salida del servidor
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                    println!("[Backend] {}", String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                    eprintln!("[Backend] {}", String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Error(error) => {
                    eprintln!("[Backend Error] {}", error);
                }
                tauri_plugin_shell::process::CommandEvent::Terminated(payload) => {
                    println!("[Backend] Process terminated with code: {:?}", payload.code);
                    break;
                }
                _ => {}
            }
        }
    });

    // Esperar un poco para que el servidor inicie
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    Ok("Backend server started successfully".to_string())
}

/// Detiene el servidor backend
#[tauri::command]
async fn stop_backend_server(server_state: State<'_, BackendServer>) -> Result<String, String> {
    let mut child_lock = server_state.child.lock().unwrap();

    if let Some(mut child) = child_lock.take() {
        child
            .kill()
            .map_err(|e| format!("Failed to kill backend server: {}", e))?;

        Ok("Backend server stopped successfully".to_string())
    } else {
        Ok("Backend server was not running".to_string())
    }
}

/// Verifica si el servidor backend está corriendo
#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    let client = reqwest::Client::new();

    match client
        .get("http://127.0.0.1:8008/api/health")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendServer::new())
        .invoke_handler(tauri::generate_handler![
            start_backend_server,
            stop_backend_server,
            check_backend_health
        ])
        .setup(|app| {
            // Iniciar el backend automáticamente al arrancar la app
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Esperar un poco para que la ventana esté lista
                tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

                // Obtener el estado del servidor
                let server_state = app_handle.state::<BackendServer>();

                // Intentar iniciar el servidor
                match start_backend_server(app_handle.clone(), server_state).await {
                    Ok(msg) => println!("[Setup] {}", msg),
                    Err(e) => eprintln!("[Setup Error] Failed to start backend: {}", e),
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Detener el backend al cerrar la ventana
                let server_state = window.state::<BackendServer>();
                tauri::async_runtime::block_on(async {
                    let _ = stop_backend_server(server_state).await;
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
