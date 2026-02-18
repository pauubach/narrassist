# Toast Migration Guide - useAppToast

## Objetivo

Migrar de llamadas directas a `toast.add()` al nuevo composable `useAppToast()`.

## Estado Actual

- **Total de ocurrencias**: 225 llamadas a `toast.add()`
- **Migradas**: ~10 en `useEntityCrud.ts` (ejemplo)
- **Pendientes**: ~215

## Patrón de Migración

### Antes
```typescript
import { useToast } from 'primevue/usetoast'

const toast = useToast()

toast.add({
  severity: 'success',
  summary: 'Guardado',
  detail: 'Operación completada',
  life: 3000,
})

toast.add({
  severity: 'error',
  summary: 'Error',
  detail: 'Algo falló',
  life: 5000,
})
```

### Después
```typescript
import { useAppToast } from '@/composables/useAppToast'

const toast = useAppToast()

toast.success('Operación completada')

toast.error('Algo falló')
```

## API del Composable

### Métodos Disponibles

```typescript
// Éxito (3s)
toast.success(message: string, options?: AppToastOptions)

// Error (5s)
toast.error(message: string, options?: AppToastOptions)

// Advertencia (4s)
toast.warn(message: string, options?: AppToastOptions)

// Info (3s)
toast.info(message: string, options?: AppToastOptions)

// Loading (no se cierra automáticamente)
const loader = toast.loading(message: string)
loader.update('Nuevo mensaje')
loader.done('Éxito!')
loader.fail('Error')

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
