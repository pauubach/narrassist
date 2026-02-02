// Menu nativo para Narrative Assistant
// Proporciona acceso rapido a las funciones principales de la aplicacion

use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    AppHandle, Emitter, Manager, Wry,
};

// ---------------------------------------------------------------------------
// Menu item IDs — el frontend escucha estos strings via "menu-event"
// ---------------------------------------------------------------------------

/// IDs del menu Archivo
pub mod file_menu {
    pub const NEW_PROJECT: &str = "new_project";
    pub const OPEN_PROJECT: &str = "open_project";
    pub const CLOSE_PROJECT: &str = "close_project";
    pub const IMPORT: &str = "import";
    pub const EXPORT: &str = "export";
    pub const SETTINGS: &str = "settings";
}

/// IDs del menu Ver
pub mod view_menu {
    pub const CHAPTERS: &str = "view_chapters";
    pub const ENTITIES: &str = "view_entities";
    pub const ALERTS: &str = "view_alerts";
    pub const RELATIONSHIPS: &str = "view_relationships";
    pub const TIMELINE: &str = "view_timeline";
    pub const TOGGLE_INSPECTOR: &str = "toggle_inspector";
    pub const TOGGLE_SIDEBAR: &str = "toggle_sidebar";
}

/// IDs del menu Analisis
pub mod analysis_menu {
    pub const RUN: &str = "run_analysis";
    pub const PAUSE: &str = "pause_analysis";
    pub const STRUCTURE: &str = "analyze_structure";
    pub const ENTITIES: &str = "analyze_entities";
    pub const CONSISTENCY: &str = "analyze_consistency";
    pub const STYLE: &str = "analyze_style";
}

/// IDs del menu Ayuda
pub mod help_menu {
    pub const TUTORIAL: &str = "tutorial";
    pub const KEYBOARD_SHORTCUTS: &str = "keyboard_shortcuts";
    pub const CHECK_UPDATES: &str = "check_updates";
    pub const ABOUT: &str = "about";
}

/// Todos los IDs de menu personalizados (no incluye predefinidos como Undo/Copy)
#[cfg(test)]
const ALL_MENU_IDS: &[&str] = &[
    file_menu::NEW_PROJECT,
    file_menu::OPEN_PROJECT,
    file_menu::CLOSE_PROJECT,
    file_menu::IMPORT,
    file_menu::EXPORT,
    file_menu::SETTINGS,
    view_menu::CHAPTERS,
    view_menu::ENTITIES,
    view_menu::ALERTS,
    view_menu::RELATIONSHIPS,
    view_menu::TIMELINE,
    view_menu::TOGGLE_INSPECTOR,
    view_menu::TOGGLE_SIDEBAR,
    analysis_menu::RUN,
    analysis_menu::PAUSE,
    analysis_menu::STRUCTURE,
    analysis_menu::ENTITIES,
    analysis_menu::CONSISTENCY,
    analysis_menu::STYLE,
    help_menu::TUTORIAL,
    help_menu::KEYBOARD_SHORTCUTS,
    help_menu::CHECK_UPDATES,
    help_menu::ABOUT,
];

/// Crea el menu principal de la aplicacion
pub fn create_menu(app: &AppHandle) -> Result<Menu<Wry>, tauri::Error> {
    // Menu Archivo
    let new_project = MenuItem::with_id(
        app,
        file_menu::NEW_PROJECT,
        "Nuevo proyecto...",
        true,
        Some("CmdOrCtrl+N"),
    )?;
    let open_project = MenuItem::with_id(
        app,
        file_menu::OPEN_PROJECT,
        "Abrir proyecto...",
        true,
        Some("CmdOrCtrl+O"),
    )?;
    let close_project = MenuItem::with_id(
        app,
        file_menu::CLOSE_PROJECT,
        "Cerrar proyecto",
        true,
        Some("CmdOrCtrl+W"),
    )?;
    let separator1 = PredefinedMenuItem::separator(app)?;
    let import = MenuItem::with_id(
        app,
        file_menu::IMPORT,
        "Importar manuscrito...",
        true,
        Some("CmdOrCtrl+I"),
    )?;
    let export = MenuItem::with_id(
        app,
        file_menu::EXPORT,
        "Exportar informe...",
        true,
        Some("CmdOrCtrl+E"),
    )?;
    let separator2 = PredefinedMenuItem::separator(app)?;
    let settings = MenuItem::with_id(
        app,
        file_menu::SETTINGS,
        "Configuracion...",
        true,
        Some("CmdOrCtrl+,"),
    )?;
    let separator3 = PredefinedMenuItem::separator(app)?;
    let quit = PredefinedMenuItem::quit(app, Some("Salir"))?;

    let file_submenu = Submenu::with_items(
        app,
        "Archivo",
        true,
        &[
            &new_project,
            &open_project,
            &close_project,
            &separator1,
            &import,
            &export,
            &separator2,
            &settings,
            &separator3,
            &quit,
        ],
    )?;

    // Menu Edicion
    let undo = PredefinedMenuItem::undo(app, Some("Deshacer"))?;
    let redo = PredefinedMenuItem::redo(app, Some("Rehacer"))?;
    let separator4 = PredefinedMenuItem::separator(app)?;
    let cut = PredefinedMenuItem::cut(app, Some("Cortar"))?;
    let copy = PredefinedMenuItem::copy(app, Some("Copiar"))?;
    let paste = PredefinedMenuItem::paste(app, Some("Pegar"))?;
    let select_all = PredefinedMenuItem::select_all(app, Some("Seleccionar todo"))?;

    let edit_submenu = Submenu::with_items(
        app,
        "Edicion",
        true,
        &[&undo, &redo, &separator4, &cut, &copy, &paste, &select_all],
    )?;

    // Menu Ver
    let view_chapters = MenuItem::with_id(
        app,
        view_menu::CHAPTERS,
        "Capitulos",
        true,
        Some("CmdOrCtrl+1"),
    )?;
    let view_entities = MenuItem::with_id(
        app,
        view_menu::ENTITIES,
        "Entidades",
        true,
        Some("CmdOrCtrl+2"),
    )?;
    let view_alerts =
        MenuItem::with_id(app, view_menu::ALERTS, "Alertas", true, Some("CmdOrCtrl+3"))?;
    let view_relationships = MenuItem::with_id(
        app,
        view_menu::RELATIONSHIPS,
        "Relaciones",
        true,
        Some("CmdOrCtrl+4"),
    )?;
    let view_timeline = MenuItem::with_id(
        app,
        view_menu::TIMELINE,
        "Linea temporal",
        true,
        Some("CmdOrCtrl+5"),
    )?;
    let separator5 = PredefinedMenuItem::separator(app)?;
    let toggle_inspector = MenuItem::with_id(
        app,
        view_menu::TOGGLE_INSPECTOR,
        "Mostrar/ocultar inspector",
        true,
        Some("CmdOrCtrl+Shift+I"),
    )?;
    let toggle_sidebar = MenuItem::with_id(
        app,
        view_menu::TOGGLE_SIDEBAR,
        "Mostrar/ocultar sidebar",
        true,
        Some("CmdOrCtrl+B"),
    )?;
    let separator6 = PredefinedMenuItem::separator(app)?;
    let fullscreen = PredefinedMenuItem::fullscreen(app, Some("Pantalla completa"))?;

    let view_submenu = Submenu::with_items(
        app,
        "Ver",
        true,
        &[
            &view_chapters,
            &view_entities,
            &view_alerts,
            &view_relationships,
            &view_timeline,
            &separator5,
            &toggle_inspector,
            &toggle_sidebar,
            &separator6,
            &fullscreen,
        ],
    )?;

    // Menu Analisis
    let run_analysis = MenuItem::with_id(
        app,
        analysis_menu::RUN,
        "Ejecutar analisis",
        true,
        Some("CmdOrCtrl+R"),
    )?;
    let pause_analysis = MenuItem::with_id(
        app,
        analysis_menu::PAUSE,
        "Pausar analisis",
        true,
        None::<&str>,
    )?;
    let separator7 = PredefinedMenuItem::separator(app)?;
    let analyze_structure = MenuItem::with_id(
        app,
        analysis_menu::STRUCTURE,
        "Analizar estructura",
        true,
        None::<&str>,
    )?;
    let analyze_entities = MenuItem::with_id(
        app,
        analysis_menu::ENTITIES,
        "Analizar entidades",
        true,
        None::<&str>,
    )?;
    let analyze_consistency = MenuItem::with_id(
        app,
        analysis_menu::CONSISTENCY,
        "Analizar consistencia",
        true,
        None::<&str>,
    )?;
    let analyze_style = MenuItem::with_id(
        app,
        analysis_menu::STYLE,
        "Analizar estilo",
        true,
        None::<&str>,
    )?;

    let analysis_submenu = Submenu::with_items(
        app,
        "Analisis",
        true,
        &[
            &run_analysis,
            &pause_analysis,
            &separator7,
            &analyze_structure,
            &analyze_entities,
            &analyze_consistency,
            &analyze_style,
        ],
    )?;

    // Menu Ayuda
    let tutorial = MenuItem::with_id(
        app,
        help_menu::TUTORIAL,
        "Tutorial de bienvenida",
        true,
        None::<&str>,
    )?;
    let keyboard_shortcuts = MenuItem::with_id(
        app,
        help_menu::KEYBOARD_SHORTCUTS,
        "Atajos de teclado",
        true,
        Some("CmdOrCtrl+/"),
    )?;
    let separator8 = PredefinedMenuItem::separator(app)?;
    let check_updates = MenuItem::with_id(
        app,
        help_menu::CHECK_UPDATES,
        "Buscar actualizaciones...",
        true,
        None::<&str>,
    )?;
    let about = MenuItem::with_id(
        app,
        help_menu::ABOUT,
        "Acerca de Narrative Assistant",
        true,
        None::<&str>,
    )?;

    let help_submenu = Submenu::with_items(
        app,
        "Ayuda",
        true,
        &[
            &tutorial,
            &keyboard_shortcuts,
            &separator8,
            &check_updates,
            &about,
        ],
    )?;

    // Construir menu completo
    Menu::with_items(
        app,
        &[
            &file_submenu,
            &edit_submenu,
            &view_submenu,
            &analysis_submenu,
            &help_submenu,
        ],
    )
}

/// Maneja los eventos del menu
pub fn handle_menu_event(app: &AppHandle, event_id: &str) {
    println!("[Menu] Event received: '{}' (len={})", event_id, event_id.len());

    // Intentar emitir al frontend via la ventana principal
    match app.get_webview_window("main") {
        Some(window) => {
            match window.emit("menu-event", event_id) {
                Ok(_) => println!("[Menu] Emitted to window 'main' OK"),
                Err(e) => {
                    println!("[Menu] emit to window failed: {e}, trying app.emit()");
                    if let Err(e2) = app.emit("menu-event", event_id) {
                        println!("[Menu] app.emit() also failed: {e2}");
                    }
                }
            }
        }
        None => {
            // Fallback: emitir a todas las ventanas via AppHandle
            println!("[Menu] Window 'main' not found, using app.emit()");
            if let Err(e) = app.emit("menu-event", event_id) {
                println!("[Menu] app.emit() failed: {e}");
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    /// Los IDs de menu deben ser unicos (sin duplicados)
    #[test]
    fn menu_ids_are_unique() {
        let mut seen = HashSet::new();
        for id in ALL_MENU_IDS {
            assert!(seen.insert(*id), "ID de menu duplicado: '{}'", id);
        }
    }

    /// Los IDs no deben estar vacios ni contener espacios
    #[test]
    fn menu_ids_are_valid_identifiers() {
        for id in ALL_MENU_IDS {
            assert!(!id.is_empty(), "ID de menu vacio encontrado");
            assert!(!id.contains(' '), "ID de menu '{}' contiene espacios", id);
            assert!(
                id.chars().all(|c| c.is_ascii_alphanumeric() || c == '_'),
                "ID de menu '{}' contiene caracteres invalidos (solo a-z, 0-9, _)",
                id
            );
        }
    }

    /// El numero total de items de menu debe coincidir con lo esperado
    /// (para detectar si se anade un item sin actualizar ALL_MENU_IDS)
    #[test]
    fn menu_ids_count_matches_expected() {
        // 6 archivo + 7 ver + 6 analisis + 4 ayuda = 23
        assert_eq!(
            ALL_MENU_IDS.len(),
            23,
            "Se cambio el numero de items de menu. Actualizar ALL_MENU_IDS y este test."
        );
    }

    /// Verifica que los IDs esperados por el frontend estan presentes
    #[test]
    fn frontend_expected_ids_exist() {
        let ids: HashSet<&str> = ALL_MENU_IDS.iter().copied().collect();

        // IDs que el frontend escucha en el listener de 'menu-event'
        let frontend_expects = [
            "new_project",
            "open_project",
            "close_project",
            "import",
            "export",
            "settings",
            "view_chapters",
            "view_entities",
            "view_alerts",
            "view_relationships",
            "view_timeline",
            "toggle_inspector",
            "toggle_sidebar",
            "run_analysis",
            "pause_analysis",
            "analyze_structure",
            "analyze_entities",
            "analyze_consistency",
            "analyze_style",
            "tutorial",
            "keyboard_shortcuts",
            "check_updates",
            "about",
        ];

        for expected_id in &frontend_expects {
            assert!(
                ids.contains(expected_id),
                "El frontend espera el ID '{}' pero no esta en ALL_MENU_IDS",
                expected_id
            );
        }
    }

    /// Verifica la organizacion por submodulos
    #[test]
    fn file_menu_ids_correct() {
        assert_eq!(file_menu::NEW_PROJECT, "new_project");
        assert_eq!(file_menu::OPEN_PROJECT, "open_project");
        assert_eq!(file_menu::CLOSE_PROJECT, "close_project");
        assert_eq!(file_menu::IMPORT, "import");
        assert_eq!(file_menu::EXPORT, "export");
        assert_eq!(file_menu::SETTINGS, "settings");
    }

    #[test]
    fn view_menu_ids_correct() {
        assert_eq!(view_menu::CHAPTERS, "view_chapters");
        assert_eq!(view_menu::ENTITIES, "view_entities");
        assert_eq!(view_menu::ALERTS, "view_alerts");
        assert_eq!(view_menu::RELATIONSHIPS, "view_relationships");
        assert_eq!(view_menu::TIMELINE, "view_timeline");
        assert_eq!(view_menu::TOGGLE_INSPECTOR, "toggle_inspector");
        assert_eq!(view_menu::TOGGLE_SIDEBAR, "toggle_sidebar");
    }

    #[test]
    fn analysis_menu_ids_correct() {
        assert_eq!(analysis_menu::RUN, "run_analysis");
        assert_eq!(analysis_menu::PAUSE, "pause_analysis");
        assert_eq!(analysis_menu::STRUCTURE, "analyze_structure");
        assert_eq!(analysis_menu::ENTITIES, "analyze_entities");
        assert_eq!(analysis_menu::CONSISTENCY, "analyze_consistency");
        assert_eq!(analysis_menu::STYLE, "analyze_style");
    }

    #[test]
    fn help_menu_ids_correct() {
        assert_eq!(help_menu::TUTORIAL, "tutorial");
        assert_eq!(help_menu::KEYBOARD_SHORTCUTS, "keyboard_shortcuts");
        assert_eq!(help_menu::CHECK_UPDATES, "check_updates");
        assert_eq!(help_menu::ABOUT, "about");
    }
}
