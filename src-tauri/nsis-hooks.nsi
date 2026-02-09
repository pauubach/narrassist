; NSIS Hooks for Narrative Assistant
; Handles:
;   - Pre-install: close running processes, offer clean install
;   - Post-install: info messages about first launch
;   - Pre-uninstall: close running processes
;   - Post-uninstall: offer granular data cleanup

!include "MUI2.nsh"

; Variable para guardar la elección del usuario sobre limpieza
Var CleanInstall

; ============================================================
; PREINSTALL - Close processes, offer clean install
; ============================================================
!macro NSIS_HOOK_PREINSTALL
    ; Cerrar procesos de Narrative Assistant antes de instalar
    DetailPrint "Cerrando procesos existentes..."

    ; Intentar cerrar la aplicación principal
    nsExec::Exec 'taskkill /F /IM "Narrative Assistant.exe" /T'
    Pop $0

    ; Cerrar el servidor backend
    nsExec::Exec 'taskkill /F /IM "narrative-assistant-server.exe" /T'
    Pop $0

    ; Esperar un momento para que los procesos se cierren
    Sleep 1000

    ; Verificar si existe una instalación previa con datos
    ; Comprobar ruta de producción (LOCALAPPDATA) y ruta de desarrollo (~/.narrative_assistant)
    IfFileExists "$LOCALAPPDATA\Narrative Assistant\data\narrative_assistant.db" 0 check_dev_path
        Goto ask_clean
    check_dev_path:
    IfFileExists "$PROFILE\.narrative_assistant\narrative_assistant.db" 0 done_clean

    ask_clean:
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "Se ha detectado una instalación anterior con datos de proyectos.$\n$\n\
            ¿Desea eliminar todos los datos anteriores y comenzar con una instalación limpia?$\n$\n\
            Seleccione 'Sí' para una instalación limpia (se perderán proyectos anteriores).$\n\
            Seleccione 'No' para conservar sus proyectos existentes." \
            IDYES clean_install IDNO keep_data

    clean_install:
        StrCpy $CleanInstall "1"
        DetailPrint "Se realizará una instalación limpia..."

        ; Eliminar base de datos (ruta de producción)
        Delete "$LOCALAPPDATA\Narrative Assistant\data\narrative_assistant.db"
        Delete "$LOCALAPPDATA\Narrative Assistant\data\narrative_assistant.db-shm"
        Delete "$LOCALAPPDATA\Narrative Assistant\data\narrative_assistant.db-wal"
        RMDir /r "$LOCALAPPDATA\Narrative Assistant\data\documents"
        RMDir /r "$LOCALAPPDATA\Narrative Assistant\data\cache"

        ; Eliminar base de datos (ruta de desarrollo legacy)
        Delete "$PROFILE\.narrative_assistant\narrative_assistant.db"
        Delete "$PROFILE\.narrative_assistant\narrative_assistant.db-shm"
        Delete "$PROFILE\.narrative_assistant\narrative_assistant.db-wal"
        RMDir /r "$PROFILE\.narrative_assistant\documents"
        RMDir /r "$PROFILE\.narrative_assistant\cache"

        ; Mantener modelos descargados (son grandes y no cambian)
        DetailPrint "Conservando modelos NLP descargados..."

        Goto done_clean

    keep_data:
        StrCpy $CleanInstall "0"
        DetailPrint "Conservando datos existentes..."

    done_clean:
    DetailPrint ""
    DetailPrint "Preparando instalacion..."
    DetailPrint ""
    DetailPrint "Se instalaran los siguientes componentes:"
    DetailPrint "  [1/4] Aplicacion Narrative Assistant"
    DetailPrint "  [2/4] Python 3.12 embebido"
    DetailPrint "  [3/4] Backend FastAPI"
    DetailPrint "  [4/4] Dependencias NLP (~1.8 GB):"
    DetailPrint "        torch, spacy, transformers,"
    DetailPrint "        sentence-transformers, numpy,"
    DetailPrint "        pandas, scipy, scikit-learn"
    DetailPrint ""
    DetailPrint "Este proceso puede tardar varios minutos"
    DetailPrint "dependiendo de la velocidad del disco."
    DetailPrint ""
!macroend

; ============================================================
; POSTINSTALL - Info messages
; ============================================================
!macro NSIS_HOOK_POSTINSTALL
    DetailPrint ""
    DetailPrint "INSTALACION COMPLETADA"
    DetailPrint ""
    DetailPrint "Componentes instalados:"
    DetailPrint "  Narrative Assistant"
    DetailPrint "  Python 3.12 embebido"
    DetailPrint "  Backend FastAPI"
    DetailPrint "  Dependencias NLP (torch, spacy, etc.)"
    DetailPrint ""
    DetailPrint "Primer inicio:"
    DetailPrint "  Se descargaran modelos NLP (~1 GB)."
    DetailPrint "  Este proceso solo ocurre una vez."
    DetailPrint ""
!macroend

; ============================================================
; PREUNINSTALL - Kill processes before removal
; ============================================================
!macro NSIS_HOOK_PREUNINSTALL
    ; Kill app processes before attempting file deletion
    DetailPrint "Cerrando procesos de Narrative Assistant..."
    nsExec::Exec 'taskkill /F /IM "Narrative Assistant.exe" /T'
    Pop $0
    nsExec::Exec 'taskkill /F /IM "narrative-assistant-server.exe" /T'
    Pop $0
    ; Wait for processes to fully terminate
    Sleep 1500
!macroend

; ============================================================
; POSTUNINSTALL - Granular data cleanup
;
; Tiers:
;   1. App cache (LOCALAPPDATA) - handled by Tauri's built-in checkbox
;   2. User projects & DB        - ask with warning (irreversible)
;   3. NLP models (~1.9 GB)      - ask (re-downloadable)
;   4. Shared dirs (Ollama, HF)  - inform only, NEVER auto-delete
; ============================================================
!macro NSIS_HOOK_POSTUNINSTALL
    ; Only clean up if user checked "Delete app data" checkbox
    ; $DeleteAppDataCheckboxState is set by Tauri's built-in
    ; uninstall confirmation page checkbox.

    ${If} $DeleteAppDataCheckboxState == 1
      ; Skip cleanup during silent/update uninstall
      StrCmp $UpdateMode 1 postuninstall_done

        ; --- Tier 1: App cache (always safe, lightweight) ---
        DetailPrint "Eliminando cache de la aplicacion..."
        RMDir /r "$PROFILE\.narrative_assistant\cache"
        RMDir /r "$PROFILE\.narrative_assistant\logs"

        ; --- Tier 2: User data (DESTRUCTIVE - ask separately) ---
        IfFileExists "$PROFILE\.narrative_assistant\narrative_assistant.db" 0 skip_userdata
        IfFileExists "$PROFILE\.narrative_assistant\data\*.*" 0 check_db_only

        check_db_only:
            ; Only DB exists (no data subdir)
            IfFileExists "$PROFILE\.narrative_assistant\narrative_assistant.db" 0 skip_userdata

            MessageBox MB_YESNO|MB_ICONEXCLAMATION \
                "Se han encontrado proyectos y datos de trabajo.$\n$\n\
                Esto incluye:$\n\
                  - Proyectos guardados$\n\
                  - Anotaciones y correcciones$\n\
                  - Historial de cambios$\n$\n\
                ESTA ACCION NO SE PUEDE DESHACER$\n$\n\
                ¿Desea eliminar sus proyectos y base de datos?" \
                /SD IDNO IDYES delete_userdata IDNO skip_userdata

        delete_userdata:
            DetailPrint "Eliminando proyectos y base de datos..."
            Delete "$PROFILE\.narrative_assistant\narrative_assistant.db"
            Delete "$PROFILE\.narrative_assistant\narrative_assistant.db-shm"
            Delete "$PROFILE\.narrative_assistant\narrative_assistant.db-wal"
            Delete "$PROFILE\.narrative_assistant\*.db"
            Delete "$PROFILE\.narrative_assistant\*.db-shm"
            Delete "$PROFILE\.narrative_assistant\*.db-wal"
            RMDir /r "$PROFILE\.narrative_assistant\data"
            RMDir /r "$PROFILE\.narrative_assistant\documents"
            Goto done_userdata

        skip_userdata:
            DetailPrint "Conservando proyectos y base de datos."

        done_userdata:

        ; --- Tier 3: NLP models (large, re-downloadable) ---
        IfFileExists "$PROFILE\.narrative_assistant\models\*.*" 0 skip_models

            MessageBox MB_YESNO|MB_ICONQUESTION \
                "Se han encontrado modelos NLP descargados (~1.9 GB).$\n$\n\
                Estos modelos se pueden volver a descargar$\n\
                automaticamente en el proximo uso.$\n$\n\
                ¿Desea eliminarlos para liberar espacio en disco?" \
                /SD IDNO IDYES delete_models IDNO skip_models

        delete_models:
            DetailPrint "Eliminando modelos NLP (~1.9 GB)..."
            RMDir /r "$PROFILE\.narrative_assistant\models"
            Goto done_models

        skip_models:
            DetailPrint "Conservando modelos NLP."

        done_models:

        ; --- Remove config ---
        Delete "$PROFILE\.narrative_assistant\config.json"
        Delete "$PROFILE\.narrative_assistant\settings.json"

        ; --- Remove parent dir if empty ---
        RMDir "$PROFILE\.narrative_assistant"

        ; --- Tier 4: Shared directories - INFORM ONLY ---
        ; Check if Ollama or HuggingFace dirs exist and inform user
        IfFileExists "$PROFILE\.ollama\*.*" 0 check_hf_exists
            Goto show_shared_info

        check_hf_exists:
        IfFileExists "$PROFILE\.cache\huggingface\*.*" 0 postuninstall_done
            Goto show_shared_info

        show_shared_info:
            MessageBox MB_OK|MB_ICONINFORMATION \
                "Los siguientes directorios contienen datos compartidos$\n\
                con otras aplicaciones y NO se han eliminado:$\n$\n\
                  $PROFILE\.ollama\    (modelos Ollama)$\n\
                  $PROFILE\.cache\huggingface\    (cache HuggingFace)$\n$\n\
                Si no utiliza Ollama o HuggingFace con otras$\n\
                aplicaciones, puede eliminar estos directorios$\n\
                manualmente para liberar espacio adicional."

    ${EndIf}

    postuninstall_done:
    DetailPrint "Desinstalacion completada."
!macroend
