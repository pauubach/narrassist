; NSIS Hooks for Narrative Assistant
; Lightweight hooks - models download handled by app on first launch

!include "MUI2.nsh"

; Variable para guardar la elección del usuario sobre limpieza
Var CleanInstall

; Hook: Called before installation starts
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
    IfFileExists "$PROFILE\.narrative_assistant\narrative_assistant.db" 0 +6
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "Se ha detectado una instalación anterior con datos de proyectos.$\n$\n\
            ¿Desea eliminar todos los datos anteriores y comenzar con una instalación limpia?$\n$\n\
            Seleccione 'Sí' para una instalación limpia (se perderán proyectos anteriores).$\n\
            Seleccione 'No' para conservar sus proyectos existentes." \
            IDYES clean_install IDNO keep_data
    
    clean_install:
        StrCpy $CleanInstall "1"
        DetailPrint "Se realizará una instalación limpia..."
        
        ; Eliminar base de datos
        Delete "$PROFILE\.narrative_assistant\narrative_assistant.db"
        Delete "$PROFILE\.narrative_assistant\narrative_assistant.db-shm"
        Delete "$PROFILE\.narrative_assistant\narrative_assistant.db-wal"
        
        ; Eliminar documentos copiados (no los originales del usuario)
        RMDir /r "$PROFILE\.narrative_assistant\documents"
        
        ; Eliminar caché
        RMDir /r "$PROFILE\.narrative_assistant\cache"
        
        ; Mantener modelos descargados (son grandes y no cambian)
        DetailPrint "Conservando modelos NLP descargados..."
        
        Goto done_clean
    
    keep_data:
        StrCpy $CleanInstall "0"
        DetailPrint "Conservando datos existentes..."
    
    done_clean:
    DetailPrint "Preparando instalacion..."
!macroend

; Hook: Called after files are installed
!macro NSIS_HOOK_POSTINSTALL
    DetailPrint "Instalacion completada."
    DetailPrint "Los modelos NLP se descargaran automaticamente al iniciar la aplicacion."
!macroend

; Hook: Uninstall
!macro NSIS_HOOK_POSTUNINSTALL
    ; Clean up is optional - user can delete ~/.narrative_assistant manually
    DetailPrint "Desinstalacion completada."
!macroend
