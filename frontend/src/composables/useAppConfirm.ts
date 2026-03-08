import { useConfirm } from 'primevue/useconfirm'

interface ConfirmActionOptions {
  header: string
  message: string
  icon?: string
  acceptLabel?: string
  rejectLabel?: string
  acceptSeverity?: 'primary' | 'secondary' | 'success' | 'info' | 'warn' | 'help' | 'danger' | 'contrast'
  acceptText?: boolean
}

export function useAppConfirm() {
  const confirm = useConfirm()

  function ask(options: ConfirmActionOptions): Promise<boolean> {
    return new Promise((resolve) => {
      confirm.require({
        header: options.header,
        message: options.message,
        icon: options.icon ?? 'pi pi-question-circle',
        rejectProps: {
          label: options.rejectLabel ?? 'Cancelar',
          severity: 'secondary',
          text: true,
        },
        acceptProps: {
          label: options.acceptLabel ?? 'Aceptar',
          severity: options.acceptSeverity ?? 'primary',
          text: options.acceptText ?? false,
        },
        accept: () => resolve(true),
        reject: () => resolve(false),
      })
    })
  }

  function confirmDanger(header: string, message: string, acceptLabel: string): Promise<boolean> {
    return ask({
      header,
      message,
      icon: 'pi pi-exclamation-triangle',
      acceptLabel,
      acceptSeverity: 'danger',
    })
  }

  return {
    ask,
    confirmDanger,
  }
}
