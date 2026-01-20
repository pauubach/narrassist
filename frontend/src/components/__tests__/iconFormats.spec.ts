/**
 * Tests para verificar el formato correcto de iconos en componentes
 *
 * PrimeIcons requiere el formato "pi pi-<icon-name>" para funcionar.
 * Usar solo "pi-<icon-name>" sin el prefijo "pi" causa que el icono no se muestre.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'fs'
import { join } from 'path'

/**
 * Busca recursivamente archivos .vue en un directorio
 */
function findVueFiles(dir: string): string[] {
  const files: string[] = []

  try {
    const entries = readdirSync(dir)

    for (const entry of entries) {
      const fullPath = join(dir, entry)
      try {
        const stat = statSync(fullPath)

        if (stat.isDirectory() && !entry.startsWith('.') && entry !== 'node_modules') {
          files.push(...findVueFiles(fullPath))
        } else if (entry.endsWith('.vue')) {
          files.push(fullPath)
        }
      } catch {
        // Ignorar archivos que no se pueden leer
      }
    }
  } catch {
    // Ignorar directorios que no se pueden leer
  }

  return files
}

/**
 * Busca usos incorrectos de iconos PrimeIcons en un archivo
 *
 * Patrones incorrectos:
 * - icon="pi-xxx" (sin prefijo "pi ")
 * - :icon="'pi-xxx'" (sin prefijo "pi ")
 *
 * Patrones correctos:
 * - icon="pi pi-xxx"
 * - :icon="'pi pi-xxx'"
 */
function findIncorrectIconUsage(content: string, filePath: string): string[] {
  const issues: string[] = []
  const lines = content.split('\n')

  lines.forEach((line, index) => {
    // Patrón: icon="pi-xxx" (incorrecto - falta "pi ")
    const staticMatch = line.match(/icon=["']pi-([^"']+)["']/g)
    if (staticMatch) {
      for (const match of staticMatch) {
        // Verificar que no sea "pi pi-xxx"
        if (!match.includes('pi pi-')) {
          issues.push(`${filePath}:${index + 1}: ${match} - Debería ser icon="pi pi-..."`)
        }
      }
    }

    // Patrón: :icon="'pi-xxx'" (incorrecto - falta "pi ")
    const dynamicMatch = line.match(/:icon=["'][^"']*pi-[^"']*["']/g)
    if (dynamicMatch) {
      for (const match of dynamicMatch) {
        if (!match.includes('pi pi-')) {
          issues.push(`${filePath}:${index + 1}: ${match} - Debería incluir "pi pi-..."`)
        }
      }
    }
  })

  return issues
}

describe('PrimeIcons Format Validation', () => {
  it('documents correct icon usage patterns', () => {
    // Patrones CORRECTOS
    const correctPatterns = [
      'icon="pi pi-users"',
      'icon="pi pi-check-circle"',
      'icon="pi pi-times"',
      ':icon="`pi pi-${iconName}`"',
    ]

    // Patrones INCORRECTOS
    const incorrectPatterns = [
      'icon="pi-users"',           // Falta "pi "
      'icon="pi-check-circle"',    // Falta "pi "
      "icon='pi-times'",           // Falta "pi " (comillas simples)
    ]

    // Verificar que los patrones correctos son detectados como válidos
    for (const pattern of correctPatterns) {
      const issues = findIncorrectIconUsage(pattern, 'test.vue')
      expect(issues).toHaveLength(0)
    }

    // Verificar que los patrones incorrectos son detectados
    for (const pattern of incorrectPatterns) {
      const issues = findIncorrectIconUsage(pattern, 'test.vue')
      expect(issues.length).toBeGreaterThan(0)
    }
  })

  it('should not find incorrect icon usage in components directory', () => {
    // Este test escanea todos los componentes .vue
    const componentsDir = join(__dirname, '..')
    const vueFiles = findVueFiles(componentsDir)

    const allIssues: string[] = []

    for (const file of vueFiles) {
      try {
        const content = readFileSync(file, 'utf-8')
        const issues = findIncorrectIconUsage(content, file)
        allIssues.push(...issues)
      } catch {
        // Ignorar archivos que no se pueden leer
      }
    }

    if (allIssues.length > 0) {
      console.error('Iconos con formato incorrecto encontrados:')
      allIssues.forEach(issue => console.error(`  ${issue}`))
    }

    expect(allIssues).toHaveLength(0)
  })

  it('should not find incorrect icon usage in views directory', () => {
    const viewsDir = join(__dirname, '../../views')
    const vueFiles = findVueFiles(viewsDir)

    const allIssues: string[] = []

    for (const file of vueFiles) {
      try {
        const content = readFileSync(file, 'utf-8')
        const issues = findIncorrectIconUsage(content, file)
        allIssues.push(...issues)
      } catch {
        // Ignorar archivos que no se pueden leer
      }
    }

    if (allIssues.length > 0) {
      console.error('Iconos con formato incorrecto encontrados:')
      allIssues.forEach(issue => console.error(`  ${issue}`))
    }

    expect(allIssues).toHaveLength(0)
  })
})

describe('Icon Usage Examples', () => {
  it('DsEmptyState should use correct icon format', () => {
    // Este test documenta el uso correcto de iconos en DsEmptyState
    const correctUsage = `
      <DsEmptyState
        icon="pi pi-users"
        title="No hay entidades"
      />
    `

    const incorrectUsage = `
      <DsEmptyState
        icon="pi-users"
        title="No hay entidades"
      />
    `

    expect(findIncorrectIconUsage(correctUsage, 'test.vue')).toHaveLength(0)
    expect(findIncorrectIconUsage(incorrectUsage, 'test.vue').length).toBeGreaterThan(0)
  })

  it('Button should use correct icon format', () => {
    const correctUsage = `
      <Button icon="pi pi-check" label="Guardar" />
    `

    const incorrectUsage = `
      <Button icon="pi-check" label="Guardar" />
    `

    expect(findIncorrectIconUsage(correctUsage, 'test.vue')).toHaveLength(0)
    expect(findIncorrectIconUsage(incorrectUsage, 'test.vue').length).toBeGreaterThan(0)
  })
})
