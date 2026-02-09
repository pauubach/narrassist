// Gestión de datos y limpieza para Narrative Assistant
//
// Proporciona comandos Tauri para:
//   - Listar categorías de datos con tamaño en disco
//   - Eliminar categorías individuales (solo datos propios, nunca compartidos)
//
// Usado por el diálogo "Gestionar datos" (macOS y Windows)

use serde::Serialize;
use std::fs;
use std::path::PathBuf;

/// Categoría de datos almacenada en disco
#[derive(Serialize, Clone)]
pub struct DataCategory {
    /// Identificador único (app_cache, user_data, models, ollama, huggingface)
    pub id: String,
    /// Nombre para mostrar en la UI
    pub label: String,
    /// Descripción breve
    pub description: String,
    /// Ruta absoluta en disco
    pub path: String,
    /// Tamaño en bytes (0 si el directorio no existe)
    pub size_bytes: u64,
    /// Si el directorio es compartido con otras aplicaciones
    pub is_shared: bool,
    /// Si la eliminación destruye datos del usuario (irreversible)
    pub is_destructive: bool,
    /// Si el directorio existe en disco
    pub exists: bool,
}

/// Calcula el tamaño total de un directorio recursivamente
fn dir_size(path: &PathBuf) -> u64 {
    if !path.exists() {
        return 0;
    }
    // Recorrido manual sin dependencia extra
    fn walk(dir: &std::path::Path) -> u64 {
        let mut total: u64 = 0;
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                if let Ok(meta) = entry.metadata() {
                    if meta.is_file() {
                        total += meta.len();
                    } else if meta.is_dir() {
                        total += walk(&entry.path());
                    }
                }
            }
        }
        total
    }
    walk(path)
}

/// Lista todas las categorías de datos con su tamaño actual
#[tauri::command]
pub fn get_data_categories() -> Vec<DataCategory> {
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return vec![],
    };

    let na = home.join(".narrative_assistant");

    // Ruta de datos de la app (Tauri LOCALAPPDATA en Windows, Application Support en macOS)
    let app_data_path = if cfg!(target_os = "windows") {
        dirs::data_local_dir()
            .unwrap_or_default()
            .join("Narrative Assistant")
    } else if cfg!(target_os = "macos") {
        dirs::data_dir()
            .unwrap_or_default()
            .join("Narrative Assistant")
    } else {
        dirs::data_dir()
            .unwrap_or_default()
            .join("narrative-assistant")
    };

    let categories = vec![
        DataCategory {
            id: "app_cache".into(),
            label: "Datos de la aplicacion".into(),
            description: "Configuracion, cache, logs del WebView".into(),
            path: app_data_path.to_string_lossy().into(),
            size_bytes: dir_size(&app_data_path),
            is_shared: false,
            is_destructive: false,
            exists: app_data_path.exists(),
        },
        DataCategory {
            id: "user_data".into(),
            label: "Proyectos y base de datos".into(),
            description: "Proyectos, anotaciones, historial de cambios".into(),
            path: na.to_string_lossy().into(),
            size_bytes: {
                // Solo contar DB + data/, no models/
                let mut s = 0u64;
                let db = na.join("narrative_assistant.db");
                if db.exists() {
                    if let Ok(m) = fs::metadata(&db) {
                        s += m.len();
                    }
                }
                s += dir_size(&na.join("data"));
                s += dir_size(&na.join("documents"));
                s
            },
            is_shared: false,
            is_destructive: true,
            exists: na.join("narrative_assistant.db").exists() || na.join("data").exists(),
        },
        DataCategory {
            id: "models".into(),
            label: "Modelos NLP".into(),
            description: "spaCy, sentence-transformers (se pueden volver a descargar)".into(),
            path: na.join("models").to_string_lossy().into(),
            size_bytes: dir_size(&na.join("models")),
            is_shared: false,
            is_destructive: false,
            exists: na.join("models").exists(),
        },
        DataCategory {
            id: "ollama".into(),
            label: "Ollama (compartido)".into(),
            description: "Modelos LLM - compartido con otras aplicaciones".into(),
            path: home.join(".ollama").to_string_lossy().into(),
            size_bytes: dir_size(&home.join(".ollama")),
            is_shared: true,
            is_destructive: false,
            exists: home.join(".ollama").exists(),
        },
        DataCategory {
            id: "huggingface".into(),
            label: "HuggingFace (compartido)".into(),
            description: "Cache de modelos - compartido con otras aplicaciones".into(),
            path: home
                .join(".cache")
                .join("huggingface")
                .to_string_lossy()
                .into(),
            size_bytes: dir_size(&home.join(".cache").join("huggingface")),
            is_shared: true,
            is_destructive: false,
            exists: home.join(".cache").join("huggingface").exists(),
        },
    ];

    categories
}

/// Elimina una categoría de datos. Rechaza eliminar directorios compartidos.
#[tauri::command]
pub fn delete_data_category(id: String) -> Result<String, String> {
    let home = dirs::home_dir().ok_or("No se pudo determinar el directorio home")?;
    let na = home.join(".narrative_assistant");

    match id.as_str() {
        "app_cache" => {
            let path = if cfg!(target_os = "windows") {
                dirs::data_local_dir()
                    .unwrap_or_default()
                    .join("Narrative Assistant")
            } else {
                dirs::data_dir()
                    .unwrap_or_default()
                    .join("Narrative Assistant")
            };
            if path.exists() {
                fs::remove_dir_all(&path)
                    .map_err(|e| format!("Error eliminando {}: {}", path.display(), e))?;
            }
            Ok("Datos de la aplicacion eliminados".into())
        }
        "user_data" => {
            // Delete DB files
            for ext in &["", "-shm", "-wal"] {
                let db = na.join(format!("narrative_assistant.db{}", ext));
                if db.exists() {
                    let _ = fs::remove_file(&db);
                }
            }
            // Delete data and documents directories
            for subdir in &["data", "documents"] {
                let path = na.join(subdir);
                if path.exists() {
                    let _ = fs::remove_dir_all(&path);
                }
            }
            // Remove parent if empty
            let _ = fs::remove_dir(&na);
            Ok("Proyectos y base de datos eliminados".into())
        }
        "models" => {
            let path = na.join("models");
            if path.exists() {
                fs::remove_dir_all(&path)
                    .map_err(|e| format!("Error eliminando modelos: {}", e))?;
            }
            // Remove parent if empty
            let _ = fs::remove_dir(&na);
            Ok("Modelos NLP eliminados".into())
        }
        "ollama" | "huggingface" => Err(
            "Los directorios compartidos no se pueden eliminar automaticamente. \
                 Eliminelos manualmente si no los utiliza con otras aplicaciones."
                .into(),
        ),
        _ => Err(format!("Categoria desconocida: {}", id)),
    }
}
