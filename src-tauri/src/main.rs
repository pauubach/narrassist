// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod cleanup;
mod menu;

#[cfg(not(debug_assertions))]
use std::io::{BufRead, BufReader};
#[cfg(test)]
use std::io::{Read, Write};
use std::process::Child;
#[cfg(not(debug_assertions))]
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
#[cfg(not(debug_assertions))]
use std::thread;
#[cfg(test)]
use std::thread;
use tauri::{AppHandle, Emitter, Manager, State};

const BACKEND_WARMING_MSG: &str = "Backend warming up (modules loading)";
const BACKEND_HEALTH_URL: &str = "http://127.0.0.1:8008/api/health";

/// Estado compartido del servidor backend
struct BackendServer {
    child: Arc<Mutex<Option<Child>>>,
    /// Flag para evitar reinicio durante el cierre de la app
    shutting_down: Arc<AtomicBool>,
}

impl BackendServer {
    fn new() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
            shutting_down: Arc::new(AtomicBool::new(false)),
        }
    }
}

fn is_backend_ready_body(body: &serde_json::Value) -> bool {
    body.get("backend_loaded")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
}

/// Liveness check: el proceso backend responde HTTP 200 (puede no tener módulos cargados).
async fn poll_health_alive() -> bool {
    poll_health_alive_url(BACKEND_HEALTH_URL).await
}

async fn poll_health_alive_url(url: &str) -> bool {
    let client = reqwest::Client::new();
    match client
        .get(url)
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

/// Readiness check: el backend responde Y tiene los módulos cargados (`backend_loaded: true`).
/// Usa esto para decidir cuándo emitir "running" al frontend.
async fn poll_health_ready() -> bool {
    poll_health_ready_url(BACKEND_HEALTH_URL).await
}

async fn poll_health_ready_url(url: &str) -> bool {
    let client = reqwest::Client::new();
    match client
        .get(url)
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => {
            if !response.status().is_success() {
                return false;
            }
            match response.json::<serde_json::Value>().await {
                Ok(body) => is_backend_ready_body(&body),
                Err(_) => false,
            }
        }
        Err(_) => false,
    }
}

async fn wait_for_health<F, Fut>(max_attempts: u32, delay_ms: u64, mut check: F) -> bool
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = bool>,
{
    for _ in 1..=max_attempts {
        if check().await {
            return true;
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(delay_ms)).await;
    }
    false
}

/// Espera a que el backend esté alive (liveness). Retorna true si responde HTTP 200.
#[cfg(not(debug_assertions))]
async fn wait_for_alive(max_attempts: u32, delay_ms: u64) -> bool {
    for attempt in 1..=max_attempts {
        if wait_for_health(1, delay_ms, poll_health_alive).await {
            println!("[Health] Backend alive after {} attempts", attempt);
            return true;
        }
    }
    false
}

/// Espera a que el backend esté ready (readiness: backend_loaded == true).
#[cfg(not(debug_assertions))]
async fn wait_for_ready(max_attempts: u32, delay_ms: u64) -> bool {
    for attempt in 1..=max_attempts {
        if wait_for_health(1, delay_ms, poll_health_ready).await {
            println!("[Health] Backend ready after {} attempts", attempt);
            return true;
        }
    }
    false
}

/// Inicia el servidor backend como sidecar
/// En modo desarrollo, asume que el servidor se ejecuta manualmente
#[tauri::command]
async fn start_backend_server(
    _app: AppHandle,
    server_state: State<'_, BackendServer>,
) -> Result<String, String> {
    // Verificar handle existente y limpiar stale handles si el proceso ya terminó.
    {
        let mut child_lock = server_state.child.lock().unwrap();
        if let Some(child) = child_lock.as_mut() {
            match child.try_wait() {
                Ok(None) => {
                    return Ok("Backend server already running".to_string());
                }
                Ok(Some(status)) => {
                    eprintln!(
                        "[Setup] Found stale backend child handle (exited with status: {:?}), cleaning up",
                        status.code()
                    );
                    *child_lock = None;
                }
                Err(e) => {
                    eprintln!(
                        "[Setup] Failed to query backend child status ({}), cleaning up handle",
                        e
                    );
                    *child_lock = None;
                }
            }
        }
    }

    // Verificar si el servidor ya esta corriendo externamente
    if poll_health_alive().await {
        println!("[Setup] Backend server already running externally");
        return Ok("Backend server already running externally".to_string());
    }

    // En modo desarrollo, indicar que se debe iniciar manualmente
    #[cfg(debug_assertions)]
    {
        println!(
            "[Setup] Development mode: start backend manually with 'python api-server/main.py'"
        );
        Ok("Development mode: start backend manually".to_string())
    }

    // En modo release, usar el sidecar
    #[cfg(not(debug_assertions))]
    {
        let mut child = spawn_embedded_backend(&_app)?;

        if let Some(stdout) = child.stdout.take() {
            spawn_output_logger(stdout, "stdout");
        }

        if let Some(stderr) = child.stderr.take() {
            spawn_output_logger(stderr, "stderr");
        }

        // HI-12: Emit "starting" so frontend knows we're polling
        let _ = _app.emit(
            "backend-status",
            serde_json::json!({
                "status": "starting",
                "message": "Iniciando servidor..."
            }),
        );

        // HI-12: Two-phase health check — liveness then readiness.
        // Phase 1: Wait for the process to respond at all (liveness).
        // 30 attempts × 500ms = 15s max.
        if !wait_for_alive(30, 500).await {
            eprintln!("[Setup] Backend process did not respond after 15s — killing");
            // Process never came alive — kill it to avoid stale handle
            let _ = child.kill();
            let _ = child.wait();
            return Err("Backend did not respond after 15s of polling".to_string());
        }

        // Process is alive — persist the handle so watchdog can manage it
        {
            let mut child_lock = server_state.child.lock().unwrap();
            *child_lock = Some(child);
        }

        // Phase 2: Wait for backend_loaded == true (readiness).
        // 60 attempts × 500ms = 30s extra for module loading.
        if !wait_for_ready(60, 500).await {
            // Process is alive but modules not loaded yet.
            // Return "warming" — NOT Err — so watchdog can still start.
            println!(
                "[Setup] Backend alive but modules not loaded after 30s — entering warming mode"
            );
            return Ok(BACKEND_WARMING_MSG.to_string());
        }

        Ok("Backend server started successfully".to_string())
    }
}

/// Detiene el servidor backend
#[tauri::command]
async fn stop_backend_server(server_state: State<'_, BackendServer>) -> Result<String, String> {
    let mut child_lock = server_state.child.lock().unwrap();

    if let Some(mut child) = child_lock.take() {
        child
            .kill()
            .map_err(|e| format!("Failed to kill backend server: {}", e))?;
        let _ = child.wait();
        Ok("Backend server stopped successfully".to_string())
    } else {
        Ok("Backend server was not running".to_string())
    }
}

/// Verifica si el servidor backend está corriendo (readiness para frontend)
#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    Ok(poll_health_ready().await)
}

/// Watchdog: monitoriza el backend y lo reinicia si se cae.
/// Se ejecuta en un loop cada 15s en release builds.
#[cfg(not(debug_assertions))]
async fn backend_watchdog(app_handle: AppHandle) {
    // Esperar a que el backend arranque inicialmente (45s para permitir carga completa)
    tokio::time::sleep(tokio::time::Duration::from_secs(45)).await;

    let mut consecutive_failures: u32 = 0;
    const MAX_FAILURES_BEFORE_RESTART: u32 = 3;
    const MAX_RESTARTS: u32 = 3;
    let mut restart_count: u32 = 0;

    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(15)).await;

        let server_state = app_handle.state::<BackendServer>();

        // No reiniciar si la app se está cerrando
        if server_state.shutting_down.load(Ordering::Relaxed) {
            println!("[Watchdog] App shutting down, stopping watchdog");
            break;
        }

        // HI-12: Use liveness (not readiness) for crash detection.
        // A backend that's alive but still loading modules should NOT trigger restart.
        if poll_health_alive().await {
            consecutive_failures = 0;
            continue;
        }

        consecutive_failures += 1;
        eprintln!(
            "[Watchdog] Health check failed ({}/{})",
            consecutive_failures, MAX_FAILURES_BEFORE_RESTART
        );

        if consecutive_failures < MAX_FAILURES_BEFORE_RESTART {
            continue;
        }

        // Backend is down - attempt restart
        if restart_count >= MAX_RESTARTS {
            eprintln!(
                "[Watchdog] Max restarts ({}) reached, giving up",
                MAX_RESTARTS
            );
            let _ = app_handle.emit(
                "backend-status",
                serde_json::json!({
                    "status": "error",
                    "message": "El servidor se detuvo y no pudo reiniciarse. Reinicia la aplicación."
                }),
            );
            break;
        }

        println!(
            "[Watchdog] Attempting backend restart ({}/{})",
            restart_count + 1,
            MAX_RESTARTS
        );

        // Notify frontend
        let _ = app_handle.emit(
            "backend-status",
            serde_json::json!({
                "status": "restarting",
                "message": "El servidor se detuvo, reiniciando..."
            }),
        );

        // Kill old process if still hanging
        {
            let mut child_lock = server_state.child.lock().unwrap();
            if let Some(mut child) = child_lock.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }

        // Spawn new process
        match spawn_embedded_backend(&app_handle) {
            Ok(mut child) => {
                if let Some(stdout) = child.stdout.take() {
                    spawn_output_logger(stdout, "stdout");
                }
                if let Some(stderr) = child.stderr.take() {
                    spawn_output_logger(stderr, "stderr");
                }

                {
                    let mut child_lock = server_state.child.lock().unwrap();
                    *child_lock = Some(child);
                }

                // Wait for readiness after restart
                if wait_for_ready(30, 500).await {
                    println!("[Watchdog] Backend restarted successfully");
                    restart_count += 1;
                    consecutive_failures = 0;

                    let _ = app_handle.emit(
                        "backend-status",
                        serde_json::json!({
                            "status": "running",
                            "message": "Servidor reiniciado correctamente"
                        }),
                    );
                } else {
                    eprintln!("[Watchdog] Backend failed to respond after restart");
                    restart_count += 1;
                }
            }
            Err(e) => {
                eprintln!("[Watchdog] Failed to spawn backend: {}", e);
                restart_count += 1;

                let _ = app_handle.emit(
                    "backend-status",
                    serde_json::json!({
                        "status": "error",
                        "message": format!("Error reiniciando servidor: {}", e)
                    }),
                );
            }
        }
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendServer::new())
        .invoke_handler(tauri::generate_handler![
            start_backend_server,
            stop_backend_server,
            check_backend_health,
            cleanup::get_data_categories,
            cleanup::delete_data_category
        ])
        .setup(|app| {
            // Configurar menu nativo
            let menu = menu::create_menu(app.handle())?;
            app.set_menu(menu)?;

            // Registrar handler de eventos del menu
            // En Tauri 2.0, on_menu_event debe llamarse en App, no en Builder
            app.on_menu_event(|app_handle, event| {
                let id = event.id();
                println!("[Menu] on_menu_event fired, id={:?}", id);
                menu::handle_menu_event(app_handle, id.as_ref());
            });

            // Forzar la ventana a primer plano (fix para cuando se lanza desde el instalador NSIS)
            // Cuando NSIS lanza la app después de la instalación, puede hacerlo en un contexto
            // diferente que causa que la ventana aparezca minimizada o detrás de otras ventanas
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
                // En Windows, también intentar traer al frente
                #[cfg(target_os = "windows")]
                {
                    let _ = window.set_always_on_top(true);
                    let _ = window.set_always_on_top(false);
                }
            }

            // Iniciar el backend automaticamente al arrancar la app
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Esperar un poco para que la ventana este lista
                tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

                // Obtener el estado del servidor
                let server_state = app_handle.state::<BackendServer>();

                // Intentar iniciar el servidor
                match start_backend_server(app_handle.clone(), server_state).await {
                    Ok(msg) => {
                        println!("[Setup] {}", msg);

                        // HI-12: Distinguish "fully ready" from "warming up"
                        let is_warming = msg == BACKEND_WARMING_MSG;
                        if is_warming {
                            // Process alive but modules still loading — emit "starting"
                            let _ = app_handle.emit(
                                "backend-status",
                                serde_json::json!({
                                    "status": "starting",
                                    "message": "Servidor iniciado, cargando módulos..."
                                }),
                            );
                        } else {
                            // Fully ready
                            let _ = app_handle.emit(
                                "backend-status",
                                serde_json::json!({
                                    "status": "running",
                                    "message": msg
                                }),
                            );
                        }

                        // HI-12: Always start watchdog when process is alive (Ok branch).
                        // The watchdog uses readiness checks, so it will detect when
                        // a warming backend finishes loading or if it crashes.
                        #[cfg(not(debug_assertions))]
                        {
                            let watchdog_handle = app_handle.clone();
                            tauri::async_runtime::spawn(backend_watchdog(watchdog_handle));
                        }
                    }
                    Err(e) => {
                        eprintln!("[Setup Error] Failed to start backend: {}", e);
                        // Emitir evento de error al frontend
                        let _ = app_handle.emit(
                            "backend-status",
                            serde_json::json!({
                                "status": "error",
                                "message": format!("Error iniciando servidor: {}", e)
                            }),
                        );
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Señalar al watchdog que pare antes de matar el backend
                let server_state = window.state::<BackendServer>();
                server_state.shutting_down.store(true, Ordering::Relaxed);

                // Detener el backend al cerrar la ventana
                tauri::async_runtime::block_on(async {
                    let _ = stop_backend_server(server_state).await;
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(not(debug_assertions))]
fn spawn_embedded_backend(app: &AppHandle) -> Result<Child, String> {
    let path_resolver = app.path();

    let resource_dir = path_resolver
        .resource_dir()
        .map_err(|e| format!("No se encontro el directorio de recursos: {}", e))?;

    let backend_root = resource_dir.join("binaries").join("backend");

    let backend_api_dir = backend_root.join("api-server");
    let main_py = backend_api_dir.join("main.py");
    if !main_py.exists() {
        return Err(format!(
            "Archivo main.py no encontrado en {}",
            main_py.display()
        ));
    }

    let python_dir = resource_dir.join("binaries").join("python-embed");

    let python_path = if cfg!(target_os = "windows") {
        python_dir.join("python.exe")
    } else if cfg!(target_os = "macos") {
        // En macOS usar el Python del framework directamente (no el wrapper)
        // El wrapper python3 en python-embed/ tiene problemas con el path
        let framework_python = python_dir
            .join("Python.framework")
            .join("Versions")
            .join("3.12")
            .join("bin")
            .join("python3");
        if framework_python.exists() {
            framework_python
        } else {
            // Fallback al wrapper si no existe el del framework
            python_dir.join("python3")
        }
    } else {
        // Linux y otros Unix
        let candidate = python_dir.join("python3");
        if candidate.exists() {
            candidate
        } else {
            python_dir.join("bin/python3")
        }
    };

    if !python_path.exists() {
        return Err(format!(
            "Python embebido no encontrado en {}",
            python_path.display()
        ));
    }

    let path_separator = if cfg!(target_os = "windows") {
        ";"
    } else {
        ":"
    };
    let mut python_path_env = format!(
        "{}{}{}",
        backend_root.display(),
        path_separator,
        backend_api_dir.display()
    );

    // En macOS, añadir site-packages del framework embebido al PYTHONPATH
    #[cfg(target_os = "macos")]
    {
        let embed_site = python_dir
            .join("Python.framework")
            .join("Versions")
            .join("3.12")
            .join("lib")
            .join("python3.12")
            .join("site-packages");

        if embed_site.exists() {
            python_path_env.push_str(path_separator);
            python_path_env.push_str(&embed_site.display().to_string());
        }
    }

    if let Ok(existing) = std::env::var("PYTHONPATH") {
        if !existing.is_empty() {
            python_path_env.push_str(path_separator);
            python_path_env.push_str(&existing);
        }
    }

    // En macOS, PYTHONHOME debe apuntar a Python.framework/Versions/3.12
    // En Windows, apunta al directorio python-embed directamente
    #[cfg(target_os = "macos")]
    let python_home = python_dir
        .join("Python.framework")
        .join("Versions")
        .join("3.12");
    #[cfg(not(target_os = "macos"))]
    let python_home = python_dir.clone();

    let mut command = Command::new(&python_path);
    command
        .arg(&main_py)
        .current_dir(&backend_api_dir)
        .env("PYTHONPATH", python_path_env)
        .env("PYTHONHOME", &python_home)
        .env("NA_EMBEDDED", "1")
        .env("NA_RESOURCE_DIR", &resource_dir)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    // En macOS, Python.framework necesita DYLD_FRAMEWORK_PATH para encontrar la libreria
    #[cfg(target_os = "macos")]
    {
        command.env("DYLD_FRAMEWORK_PATH", &python_dir);

        // CRITICAL: Crear symlink Python en binaries/ si no existe
        // El ejecutable python3 busca @executable_path/../Python que debe apuntar a
        // python-embed/Python.framework/Versions/3.12/Python
        let python_symlink = resource_dir.join("binaries").join("Python");
        let python_lib = python_dir
            .join("Python.framework")
            .join("Versions")
            .join("3.12")
            .join("Python");

        if !python_symlink.exists() && python_lib.exists() {
            use std::os::unix::fs::symlink;
            let relative_target = std::path::Path::new("python-embed")
                .join("Python.framework")
                .join("Versions")
                .join("3.12")
                .join("Python");
            if let Err(e) = symlink(&relative_target, &python_symlink) {
                eprintln!("[TAURI] Failed to create Python symlink: {}", e);
            }
        }
    }

    // En Windows, evitar que se muestre una ventana de consola para Python
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    command
        .spawn()
        .map_err(|e| format!("Failed to spawn backend process: {}", e))
}

#[cfg(not(debug_assertions))]
fn spawn_output_logger<T>(reader: T, label: &'static str)
where
    T: std::io::Read + Send + 'static,
{
    thread::spawn(move || {
        let buf_reader = BufReader::new(reader);
        for line in buf_reader.lines() {
            match line {
                Ok(content) => {
                    if label == "stderr" {
                        eprintln!("[Backend {}] {}", label, content);
                    } else {
                        println!("[Backend {}] {}", label, content);
                    }
                }
                Err(err) => {
                    eprintln!("[Backend {}] Error leyendo salida: {}", label, err);
                    break;
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    fn spawn_mock_health_server(responses: Vec<String>) -> String {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind mock server");
        let addr = listener.local_addr().expect("listener addr");
        let responses = Arc::new(responses);
        let counter = Arc::new(AtomicUsize::new(0));

        let responses_clone = Arc::clone(&responses);
        let counter_clone = Arc::clone(&counter);

        thread::spawn(move || {
            for stream in listener.incoming() {
                let mut stream = match stream {
                    Ok(stream) => stream,
                    Err(_) => break,
                };

                let mut buffer = [0_u8; 1024];
                let _ = stream.read(&mut buffer);

                let idx = counter_clone.fetch_add(1, Ordering::SeqCst);
                let response = responses_clone
                    .get(idx)
                    .or_else(|| responses_clone.last())
                    .expect("mock response");

                let _ = stream.write_all(response.as_bytes());
                let _ = stream.flush();

                if idx + 1 >= responses_clone.len() {
                    break;
                }
            }
        });

        format!("http://{}/api/health", addr)
    }

    fn json_response(body: &str) -> String {
        format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        )
    }

    fn ok_response(body: &str) -> String {
        format!(
            "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        )
    }

    #[test]
    fn backend_ready_body_requires_explicit_flag() {
        assert!(is_backend_ready_body(
            &serde_json::json!({ "backend_loaded": true })
        ));
        assert!(!is_backend_ready_body(
            &serde_json::json!({ "backend_loaded": false })
        ));
        assert!(!is_backend_ready_body(
            &serde_json::json!({ "status": "ok" })
        ));
    }

    #[tokio::test]
    async fn poll_health_alive_accepts_http_200() {
        let url = spawn_mock_health_server(vec![ok_response("ok")]);

        assert!(poll_health_alive_url(&url).await);
    }

    #[tokio::test]
    async fn poll_health_ready_requires_backend_loaded_true() {
        let url = spawn_mock_health_server(vec![json_response(r#"{"backend_loaded":false}"#)]);

        assert!(!poll_health_ready_url(&url).await);
    }

    #[tokio::test]
    async fn wait_for_health_retries_until_backend_is_ready() {
        let url = spawn_mock_health_server(vec![
            json_response(r#"{"backend_loaded":false}"#),
            json_response(r#"{"backend_loaded":true}"#),
        ]);

        let ready = wait_for_health(3, 10, || poll_health_ready_url(&url)).await;

        assert!(ready);
    }

    #[tokio::test]
    async fn poll_health_alive_rejects_non_success_http_status() {
        let response =
            "HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
        let url = spawn_mock_health_server(vec![response.to_string()]);

        assert!(!poll_health_alive_url(&url).await);
    }

    #[tokio::test]
    async fn poll_health_ready_rejects_invalid_json_payload() {
        let url = spawn_mock_health_server(vec![ok_response("backend warming up")]);

        assert!(!poll_health_ready_url(&url).await);
    }

    #[tokio::test]
    async fn wait_for_health_returns_false_when_backend_never_becomes_ready() {
        let url = spawn_mock_health_server(vec![
            json_response(r#"{"backend_loaded":false}"#),
            json_response(r#"{"backend_loaded":false}"#),
            json_response(r#"{"backend_loaded":false}"#),
        ]);

        let ready = wait_for_health(3, 10, || poll_health_ready_url(&url)).await;

        assert!(!ready);
    }
}
