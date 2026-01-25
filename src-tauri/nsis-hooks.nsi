; NSIS Hooks for Narrative Assistant
; Lightweight hooks - models download handled by app on first launch

!include "MUI2.nsh"

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
