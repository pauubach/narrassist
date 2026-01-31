// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod menu;

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::{AppHandle, Emitter, Manager, State};

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
/// En modo desarrollo, asume que el servidor se ejecuta manualmente
#[tauri::command]
async fn start_backend_server(
    _app: AppHandle,
    server_state: State<'_, BackendServer>,
) -> Result<String, String> {
    // Verificar si ya esta corriendo (scope limitado para el lock)
    {
        let child_lock = server_state.child.lock().unwrap();
        if child_lock.is_some() {
            return Ok("Backend server already running".to_string());
        }
    }

    // Verificar si el servidor ya esta corriendo externamente
    let client = reqwest::Client::new();
    if let Ok(response) = client
        .get("http://127.0.0.1:8008/api/health")
        .timeout(std::time::Duration::from_secs(1))
        .send()
        .await
    {
        if response.status().is_success() {
            println!("[Setup] Backend server already running externally");
            return Ok("Backend server already running externally".to_string());
        }
    }

    // En modo desarrollo, indicar que se debe iniciar manualmente
    #[cfg(debug_assertions)]
    {
        println!(
            "[Setup] Development mode: start backend manually with 'python api-server/main.py'"
        );
        return Ok("Development mode: start backend manually".to_string());
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

        {
            let mut child_lock = server_state.child.lock().unwrap();
            *child_lock = Some(child);
        }

        // Esperar un momento para que el servidor arranque
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

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
        .manage(BackendServer::new())
        .invoke_handler(tauri::generate_handler![
            start_backend_server,
            stop_backend_server,
            check_backend_health
        ])
        .setup(|app| {
            // Configurar menu nativo
            let menu = menu::create_menu(app.handle())?;
            app.set_menu(menu)?;

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
                        // Emitir evento al frontend indicando que el backend está listo
                        let _ = app_handle.emit(
                            "backend-status",
                            serde_json::json!({
                                "status": "running",
                                "message": msg
                            }),
                        );
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
        .on_menu_event(|app, event| {
            menu::handle_menu_event(app, event.id().as_ref());
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
    } else {
        // En macOS el script crea un symlink python3
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

    if let Ok(existing) = std::env::var("PYTHONPATH") {
        if !existing.is_empty() {
            python_path_env.push_str(path_separator);
            python_path_env.push_str(&existing);
        }
    }

    let mut command = Command::new(&python_path);
    command
        .arg(&main_py)
        .current_dir(&backend_api_dir)
        .env("PYTHONPATH", python_path_env)
        .env("PYTHONHOME", &python_dir)
        .env("NA_EMBEDDED", "1")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

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
