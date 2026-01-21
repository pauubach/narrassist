; NSIS Hooks for Narrative Assistant
; Lightweight hooks - models download handled by app on first launch

!include "MUI2.nsh"

; Hook: Called before installation starts
!macro NSIS_HOOK_PREINSTALL
    ; Simple pre-install check - no disk space validation to avoid NSIS issues
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
