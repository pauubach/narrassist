/**
 * useAlertExport - Exportación de alertas en CSV/JSON.
 *
 * Extraído de AlertsDashboard para reutilización.
 */

import { useToast } from 'primevue/usetoast'
import type { MenuItem } from 'primevue/menuitem'
import type { Alert } from '@/types'

/**
 * Descarga un Blob como archivo.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Composable para exportar alertas en CSV y JSON.
 */
export function useAlertExport(projectId: () => number) {
  const toast = useToast()

  function exportCsv(alerts: Alert[]): void {
    const headers = ['ID', 'Severidad', 'Categoría', 'Estado', 'Capítulo', 'Título', 'Descripción', 'Confianza', 'Fecha']
    const rows = alerts.map(a => [
      a.id,
      a.severity,
      a.category || '',
      a.status,
      a.chapter || '',
      `"${(a.title || '').replace(/"/g, '""')}"`,
      `"${(a.description || '').replace(/"/g, '""')}"`,
      a.confidence ? (a.confidence * 100).toFixed(0) + '%' : '',
      a.createdAt || ''
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    downloadBlob(blob, `alertas_proyecto_${projectId()}.csv`)
    toast.add({ severity: 'success', summary: 'Exportado', detail: `${alerts.length} alertas exportadas (CSV)`, life: 3000 })
  }

  function exportJson(alerts: Alert[]): void {
    const content = {
      projectId: projectId(),
      exportedAt: new Date().toISOString(),
      totalAlerts: alerts.length,
      bySeverity: {
        critical: alerts.filter(a => a.severity === 'critical').length,
        high: alerts.filter(a => a.severity === 'high').length,
        medium: alerts.filter(a => a.severity === 'medium').length,
        low: alerts.filter(a => a.severity === 'low').length,
        info: alerts.filter(a => a.severity === 'info').length,
      },
      byStatus: {
        active: alerts.filter(a => a.status === 'active').length,
        resolved: alerts.filter(a => a.status === 'resolved').length,
        dismissed: alerts.filter(a => a.status === 'dismissed').length,
      },
      alerts: alerts.map(a => ({
        id: a.id,
        title: a.title,
        description: a.description,
        severity: a.severity,
        category: a.category,
        status: a.status,
        chapter: a.chapter,
        confidence: a.confidence,
        createdAt: a.createdAt,
      })),
    }

    const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
    downloadBlob(blob, `alertas_proyecto_${projectId()}.json`)
    toast.add({ severity: 'success', summary: 'Exportado', detail: `${alerts.length} alertas exportadas (JSON)`, life: 3000 })
  }

  function exportAlerts(alerts: Alert[], format: 'csv' | 'json' = 'csv'): void {
    if (!alerts || alerts.length === 0) {
      toast.add({ severity: 'warn', summary: 'Sin datos', detail: 'No hay alertas para exportar', life: 4000 })
      return
    }

    try {
      if (format === 'csv') {
        exportCsv(alerts)
      } else {
        exportJson(alerts)
      }
    } catch (err) {
      console.error('Error exporting alerts:', err)
      toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar alertas', life: 5000 })
    }
  }

  const exportMenuItems: MenuItem[] = [
    {
      label: 'Exportar CSV',
      icon: 'pi pi-file',
      command: () => {} // Se debe sobrescribir al usarlo (necesita referencia a las alertas filtradas)
    },
    {
      label: 'Exportar JSON',
      icon: 'pi pi-code',
      command: () => {}
    }
  ]

  function getExportMenuItems(alertsGetter: () => Alert[]): MenuItem[] {
    return [
      {
        label: 'Exportar CSV',
        icon: 'pi pi-file',
        command: () => exportAlerts(alertsGetter(), 'csv')
      },
      {
        label: 'Exportar JSON',
        icon: 'pi pi-code',
        command: () => exportAlerts(alertsGetter(), 'json')
      }
    ]
  }

  return { exportAlerts, exportCsv, exportJson, downloadBlob, exportMenuItems, getExportMenuItems }
}
