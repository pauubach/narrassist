; NSIS Hooks for Narrative Assistant
; This file is included by the Tauri NSIS installer template
; It adds post-installation model download functionality

!include "MUI2.nsh"
!include "nsDialogs.nsh"

; Variables for the model download page
Var ModelDownloadPage
Var ModelDownloadLabel
Var ModelDownloadProgress
Var ModelDownloadStatus

; Custom page for downloading models
Function ModelDownloadPageCreate
    ; Create the page
    nsDialogs::Create 1018
    Pop $ModelDownloadPage

    ${If} $ModelDownloadPage == error
        Abort
    ${EndIf}

    ; Title
    ${NSD_CreateLabel} 0 0 100% 30u "Descargando modelos necesarios..."
    Pop $ModelDownloadLabel
    SendMessage $ModelDownloadLabel ${WM_SETFONT} $mui.Header.Text.Font 0

    ; Progress bar
    ${NSD_CreateProgressBar} 0 50u 100% 20u ""
    Pop $ModelDownloadProgress

    ; Status text
    ${NSD_CreateLabel} 0 80u 100% 40u "Esto puede tardar unos minutos. Los modelos se descargan una sola vez y permiten el funcionamiento offline."
    Pop $ModelDownloadStatus

    nsDialogs::Show
FunctionEnd

Function ModelDownloadPageLeave
    ; This runs when leaving the page
FunctionEnd

; Hook: Called after files are installed
!macro NSIS_HOOK_POSTINSTALL
    ; Show a message that we're downloading models
    DetailPrint "Descargando modelos NLP..."

    ; Check if Python is available
    nsExec::ExecToStack 'python --version'
    Pop $0

    ${If} $0 != 0
        ; Python not found, try python3
        nsExec::ExecToStack 'python3 --version'
        Pop $0

        ${If} $0 != 0
            ; No Python, skip model download and let app handle it
            DetailPrint "Python no encontrado. Los modelos se descargaran al iniciar la aplicacion."
            Goto PostInstallDone
        ${EndIf}

        StrCpy $1 "python3"
    ${Else}
        StrCpy $1 "python"
    ${EndIf}

    ; Run install_models.py with silent mode
    DetailPrint "Ejecutando install_models.py..."
    SetDetailsPrint both

    ; Execute the model installation script
    nsExec::ExecToLog '$1 "$INSTDIR\resources\install_models.py" --silent'
    Pop $0

    ${If} $0 == 0
        DetailPrint "Modelos descargados correctamente."
    ${Else}
        DetailPrint "Nota: Los modelos se descargaran al iniciar la aplicacion."
    ${EndIf}

    PostInstallDone:
!macroend

; Hook: Called before installation starts
!macro NSIS_HOOK_PREINSTALL
    ; Check disk space (need ~2GB for models)
    ${GetRoot} "$INSTDIR" $0
    ${DriveSpace} "$0\" "/D=F /S=M" $1

    ${If} $1 < 2048
        MessageBox MB_YESNO|MB_ICONWARNING \
            "Se recomienda al menos 2 GB de espacio libre para descargar los modelos necesarios.$\n$\nEspacio disponible: $1 MB$\n$\n¿Desea continuar de todos modos?" \
            IDYES ContinueInstall
        Abort
        ContinueInstall:
    ${EndIf}
!macroend

; Hook: Uninstall - clean up model cache (optional)
!macro NSIS_HOOK_POSTUNINSTALL
    ; Ask user if they want to remove downloaded models
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "¿Desea eliminar también los modelos descargados?$\n$\n(Se encuentran en $PROFILE\.narrative_assistant y ocupan aproximadamente 1 GB)" \
        IDNO SkipModelCleanup

    ; Remove model directory
    RMDir /r "$PROFILE\.narrative_assistant"

    SkipModelCleanup:
!macroend
