# Toast Migration Guide - useAppToast

## Objetivo

Migrar de llamadas directas a `toast.add()` al nuevo composable `useAppToast()`.

## Estado Actual

- **Total de ocurrencias**: 225 llamadas a `toast.add()`
- **Migradas**: 16 en `useEntityCrud.ts` (ejemplo completo) ✅
- **Pendientes**: ~209

## Patrón de Migración

### Antes
```typescript
import { useToast } from 'primevue/usetoast'

const toast = useToast()

toast.add({
  severity: 'success',
  summary: 'Guardado',
  detail: 'Cambios guardados correctamente',
  life: 3000,
})

toast.add({
  severity: 'error',
  summary: 'Error',
  detail: 'No se pudo guardar',
  life: 5000,
})
```

### Después
```typescript
import { useAppToast } from '@/composables/useAppToast'

const toast = useAppToast()

// Método semántico específico
toast.saved('Cambios guardados correctamente')

// Genérico (fallback)
toast.error('No se pudo guardar')
```

## API del Composable

### Métodos CRUD (5)

```typescript
// Crear nuevo recurso
toast.created('Nueva entidad añadida')

// Guardar cambios (también para exportar, aplicar config)
toast.saved('Cambios guardados correctamente')
toast.saved('Alertas exportadas como CSV')
toast.saved('Configuración aplicada')

// Actualizar existente
toast.updated('Entidad actualizada correctamente')

// Eliminar
toast.deleted('Alerta eliminada permanentemente')

// Restaurar (también para importar)
toast.restored('Entidad restaurada desde papelera')
toast.restored('Trabajo editorial importado correctamente')
```

### Métodos Especiales (2)

```typescript
// Fusionar entidades
toast.merged('2 entidades fusionadas en "Personaje Principal"')

// Separar fusión
toast.separated('Fusión deshecha, entidades restauradas')
```

### Métodos Genéricos (5)

```typescript
// Éxito (3s)
toast.success('Operación completada')

// Error (5s)
toast.error('No se pudo completar la operación')

// Advertencia (4s)
toast.warn('El archivo es muy grande')

// Info (3s)
toast.info('Se requiere reiniciar')

// Loading (no se cierra automáticamente)
const loader = toast.loading('Procesando...')
loader.update('Procesando capítulo 5 de 45...')
loader.done('Análisis completado')
loader.fail('Error al procesar')

// Limpiar todos
toast.clear()
```

### Opciones

```typescript
interface AppToastOptions {
  life?: number        // Duración en ms
  closable?: boolean   // Permite cerrar (default: true)
  group?: string       // Grupo de toast
}

// Para success, error, warn, info: también summary personalizado
toast.success('Mensaje', { summary: 'Custom Summary' })
```

## Script de Migración Automática

```bash
# Migrar archivos de composables
cd frontend/src/composables
for file in *.ts; do
  # Cambiar import
  sed -i "s/import { useToast } from 'primevue\/usetoast'/import { useAppToast } from '.\/useAppToast'/g" "$file"

  # Cambiar uso
  sed -i 's/const toast = useToast()/const toast = useAppToast()/g' "$file"

  # Migrar success
  perl -i -pe "s/toast\.add\(\{\s*severity: 'success',\s*summary: '[^']*',\s*detail: '([^']*)',\s*life: \d+,?\s*\}\)/toast.success('\$1')/gs" "$file"

  # Migrar error
  perl -i -pe "s/toast\.add\(\{\s*severity: 'error',\s*summary: '[^']*',\s*detail: '([^']*)',\s*life: \d+,?\s*\}\)/toast.error('\$1')/gs" "$file"
done
```

## Archivos Prioritarios para Migrar

### Composables (7 archivos)
- [x] `useEntityCrud.ts` ✅
- [ ] `useAlertExport.ts`
- [ ] `useGlobalUndo.ts`
- [ ] `useNLPMethods.ts`
- [ ] `useOllamaManagement.ts`
- [ ] `useSettingsPersistence.ts`

### Stores (varios)
- [ ] `alerts.ts`
- [ ] `entities.ts`
- [ ] `projects.ts`
- [ ] `settings.ts`

### Views (10+ archivos)
- [ ] `AlertsView.vue`
- [ ] `CharacterView.vue`
- [ ] `CollectionDetailView.vue`
- [ ] `HomeView.vue`
- [ ] `SettingsView.vue`

### Components (30+ archivos)
- [ ] `workspace/AlertsDashboard.vue`
- [ ] `workspace/EntitiesTab.vue`
- [ ] Y muchos más...

## Beneficios

1. **Menos código**: De 6 líneas a 1 línea
2. **Consistencia**: Todos los toasts usan el mismo estilo
3. **Mantenibilidad**: Cambios centralizados en un solo lugar
4. **Type safety**: Mejor inferencia de tipos
5. **Funcionalidad extra**: `loading()` con updates dinámicos

## Testing

Después de migrar, verificar:
- Los mensajes siguen apareciendo correctamente
- Las duraciones son apropiadas
- Los estilos están correctos
- No hay errores en consola

## Notas

- La migración es **opcional pero recomendada**
- Puede hacerse gradualmente (archivo por archivo)
- No afecta funcionalidad existente
- Ambos sistemas pueden coexistir temporalmente
