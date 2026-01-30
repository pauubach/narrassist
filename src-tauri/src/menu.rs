// Menu nativo para Narrative Assistant
// Proporciona acceso rapido a las funciones principales de la aplicacion

use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    AppHandle, Emitter, Manager, Wry,
};

/// Crea el menu principal de la aplicacion
pub fn create_menu(app: &AppHandle) -> Result<Menu<Wry>, tauri::Error> {
    // Menu Archivo
    let new_project = MenuItem::with_id(app, "new_project", "Nuevo proyecto...", true, Some("CmdOrCtrl+N"))?;
    let open_project = MenuItem::with_id(app, "open_project", "Abrir proyecto...", true, Some("CmdOrCtrl+O"))?;
    let close_project = MenuItem::with_id(app, "close_project", "Cerrar proyecto", true, Some("CmdOrCtrl+W"))?;
    let separator1 = PredefinedMenuItem::separator(app)?;
    let import = MenuItem::with_id(app, "import", "Importar manuscrito...", true, Some("CmdOrCtrl+I"))?;
    let export = MenuItem::with_id(app, "export", "Exportar informe...", true, Some("CmdOrCtrl+E"))?;
    let separator2 = PredefinedMenuItem::separator(app)?;
    let settings = MenuItem::with_id(app, "settings", "Configuracion...", true, Some("CmdOrCtrl+,"))?;
    let separator3 = PredefinedMenuItem::separator(app)?;
    let quit = PredefinedMenuItem::quit(app, Some("Salir"))?;

    let file_menu = Submenu::with_items(
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

    let edit_menu = Submenu::with_items(
        app,
        "Edicion",
        true,
        &[
            &undo,
            &redo,
            &separator4,
            &cut,
            &copy,
            &paste,
            &select_all,
        ],
    )?;

    // Menu Ver
    let view_chapters = MenuItem::with_id(app, "view_chapters", "Capitulos", true, Some("CmdOrCtrl+1"))?;
    let view_entities = MenuItem::with_id(app, "view_entities", "Entidades", true, Some("CmdOrCtrl+2"))?;
    let view_alerts = MenuItem::with_id(app, "view_alerts", "Alertas", true, Some("CmdOrCtrl+3"))?;
    let view_relationships = MenuItem::with_id(app, "view_relationships", "Relaciones", true, Some("CmdOrCtrl+4"))?;
    let view_timeline = MenuItem::with_id(app, "view_timeline", "Linea temporal", true, Some("CmdOrCtrl+5"))?;
    let separator5 = PredefinedMenuItem::separator(app)?;
    let toggle_inspector = MenuItem::with_id(app, "toggle_inspector", "Mostrar/ocultar inspector", true, Some("CmdOrCtrl+I"))?;
    let toggle_sidebar = MenuItem::with_id(app, "toggle_sidebar", "Mostrar/ocultar sidebar", true, Some("CmdOrCtrl+B"))?;
    let separator6 = PredefinedMenuItem::separator(app)?;
    let fullscreen = PredefinedMenuItem::fullscreen(app, Some("Pantalla completa"))?;

    let view_menu = Submenu::with_items(
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
    let run_analysis = MenuItem::with_id(app, "run_analysis", "Ejecutar analisis", true, Some("CmdOrCtrl+R"))?;
    let pause_analysis = MenuItem::with_id(app, "pause_analysis", "Pausar analisis", true, None::<&str>)?;
    let separator7 = PredefinedMenuItem::separator(app)?;
    let analyze_structure = MenuItem::with_id(app, "analyze_structure", "Analizar estructura", true, None::<&str>)?;
    let analyze_entities = MenuItem::with_id(app, "analyze_entities", "Analizar entidades", true, None::<&str>)?;
    let analyze_consistency = MenuItem::with_id(app, "analyze_consistency", "Analizar consistencia", true, None::<&str>)?;
    let analyze_style = MenuItem::with_id(app, "analyze_style", "Analizar estilo", true, None::<&str>)?;

    let analysis_menu = Submenu::with_items(
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
    let tutorial = MenuItem::with_id(app, "tutorial", "Tutorial de bienvenida", true, None::<&str>)?;
    let keyboard_shortcuts = MenuItem::with_id(app, "keyboard_shortcuts", "Atajos de teclado", true, Some("CmdOrCtrl+/"))?;
    let separator8 = PredefinedMenuItem::separator(app)?;
    let check_updates = MenuItem::with_id(app, "check_updates", "Buscar actualizaciones...", true, None::<&str>)?;
    let about = MenuItem::with_id(app, "about", "Acerca de Narrative Assistant", true, None::<&str>)?;

    let help_menu = Submenu::with_items(
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
            &file_menu,
            &edit_menu,
            &view_menu,
            &analysis_menu,
            &help_menu,
        ],
    )
}

/// Maneja los eventos del menu
pub fn handle_menu_event(app: &AppHandle, event_id: &str) {
    // Emitir evento al frontend
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.emit("menu-event", event_id);
    }

    // Log para debugging
    println!("[Menu] Event: {}", event_id);
}
