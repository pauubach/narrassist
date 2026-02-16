<template>
  <!-- Modo claro/oscuro/auto -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Modo de apariencia</label>
      <p class="setting-description">Elige entre modo claro, oscuro o automático según el sistema</p>
    </div>
    <div class="setting-control">
      <SelectButton
        :model-value="themeStore.config.mode"
        :options="modeOptions"
        option-label="label"
        option-value="value"
        @update:model-value="(val) => themeStore.setMode(val)"
      />
    </div>
  </div>

  <!-- Estilo visual (preset) -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Estilo visual</label>
      <p class="setting-description">Selecciona el estilo base de la interfaz. Los temas de escritura están optimizados para largas sesiones de lectura.</p>
    </div>
    <div class="setting-control wide">
      <Select
        :model-value="themeStore.config.preset"
        :options="groupedPresetOptions"
        option-label="label"
        option-value="value"
        option-group-label="label"
        option-group-children="items"
        class="preset-dropdown"
        @update:model-value="onPresetChange"
      >
        <template #value="slotProps">
          <div v-if="slotProps.value" class="preset-selected">
            <span class="preset-name">{{ getPresetName(slotProps.value) }}</span>
          </div>
          <span v-else>Selecciona un tema</span>
        </template>
        <template #optiongroup="slotProps">
          <div class="preset-group-header">
            <i :class="getCategoryIcon(slotProps.option.label)"></i>
            <span>{{ slotProps.option.label }}</span>
          </div>
        </template>
        <template #option="slotProps">
          <div class="preset-option">
            <div class="preset-info">
              <span class="preset-name">{{ slotProps.option.label }}</span>
              <span class="preset-desc">{{ slotProps.option.description }}</span>
            </div>
          </div>
        </template>
      </Select>
    </div>
  </div>

  <!-- Color primario -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Color primario</label>
      <p class="setting-description">Color de acento para botones, enlaces y elementos destacados</p>
    </div>
    <div class="setting-control wide">
      <div class="color-palette">
        <button
          v-for="color in PRIMARY_COLORS"
          :key="color.name"
          class="color-swatch"
          :class="{ active: themeStore.config.primaryColor === color.value }"
          :style="{ backgroundColor: color.value }"
          :title="color.label"
          @click="themeStore.setPrimaryColor(color.value)"
        >
          <i v-if="themeStore.config.primaryColor === color.value" class="pi pi-check"></i>
        </button>
      </div>
    </div>
  </div>

  <!-- Fuente de interfaz -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Fuente de interfaz</label>
      <p class="setting-description">Tipografía para menús, botones y controles</p>
    </div>
    <div class="setting-control wide">
      <Select
        :model-value="themeStore.config.fontFamily"
        :options="groupedFontOptions"
        option-label="label"
        option-value="value"
        option-group-label="label"
        option-group-children="items"
        class="font-dropdown"
        @update:model-value="onFontFamilyChange"
      >
        <template #value="slotProps">
          <span v-if="slotProps.value" :class="`font-${slotProps.value}`">
            {{ getFontFamilyLabel(slotProps.value) }}
          </span>
        </template>
        <template #optiongroup="slotProps">
          <div class="font-group-header">
            <i :class="slotProps.option.label === 'Generales' ? 'pi pi-desktop' : 'pi pi-book'"></i>
            <span>{{ slotProps.option.label }}</span>
          </div>
        </template>
        <template #option="slotProps">
          <div class="font-option" :class="`font-${slotProps.option.value}`">
            <span class="font-name">{{ slotProps.option.label }}</span>
            <span class="font-desc">{{ slotProps.option.description }}</span>
          </div>
        </template>
      </Select>
    </div>
  </div>

  <!-- Fuente de lectura -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Fuente de lectura</label>
      <p class="setting-description">Tipografía para visualizar el manuscrito</p>
    </div>
    <div class="setting-control wide">
      <Select
        :model-value="themeStore.config.fontFamilyReading"
        :options="groupedFontOptions"
        option-label="label"
        option-value="value"
        option-group-label="label"
        option-group-children="items"
        class="font-dropdown"
        @update:model-value="onFontFamilyReadingChange"
      >
        <template #value="slotProps">
          <span v-if="slotProps.value" :class="`font-${slotProps.value}`">
            {{ getFontFamilyLabel(slotProps.value) }}
          </span>
        </template>
        <template #optiongroup="slotProps">
          <div class="font-group-header">
            <i :class="slotProps.option.label === 'Generales' ? 'pi pi-desktop' : 'pi pi-book'"></i>
            <span>{{ slotProps.option.label }}</span>
          </div>
        </template>
        <template #option="slotProps">
          <div class="font-option" :class="`font-${slotProps.option.value}`">
            <span class="font-name">{{ slotProps.option.label }}</span>
            <span class="font-desc">{{ slotProps.option.description }}</span>
          </div>
        </template>
      </Select>
    </div>
  </div>

  <!-- Controles compactos: 2 columnas en pantallas anchas -->
  <div class="compact-settings-grid">
    <div class="setting-item">
      <div class="setting-info">
        <label class="setting-label">Tamaño de fuente</label>
        <p class="setting-description">Tamaño base del texto</p>
      </div>
      <div class="setting-control">
        <SelectButton
          :model-value="themeStore.config.fontSize"
          :options="fontSizeOptions"
          option-label="label"
          option-value="value"
          @update:model-value="(val) => themeStore.setFontSize(val)"
        />
      </div>
    </div>

    <div class="setting-item">
      <div class="setting-info">
        <label class="setting-label">Interlineado</label>
        <p class="setting-description">Espaciado entre líneas</p>
      </div>
      <div class="setting-control">
        <Select
          :model-value="themeStore.config.lineHeight"
          :options="lineHeightOptions"
          option-label="label"
          option-value="value"
          @update:model-value="onLineHeightChange"
        />
      </div>
    </div>

    <div class="setting-item">
      <div class="setting-info">
        <label class="setting-label">Bordes redondeados</label>
        <p class="setting-description">Redondeo en botones y tarjetas</p>
      </div>
      <div class="setting-control">
        <SelectButton
          :model-value="themeStore.config.radius"
          :options="radiusOptions"
          option-label="label"
          option-value="value"
          @update:model-value="(val) => themeStore.setRadius(val)"
        />
      </div>
    </div>

    <div class="setting-item">
      <div class="setting-info">
        <label class="setting-label">Densidad de la interfaz</label>
        <p class="setting-description">Espaciado entre elementos</p>
      </div>
      <div class="setting-control">
        <SelectButton
          :model-value="themeStore.config.compactness"
          :options="compactnessOptions"
          option-label="label"
          option-value="value"
          @update:model-value="(val) => themeStore.setCompactness(val)"
        />
      </div>
    </div>
  </div>

  <!-- Reducir animaciones -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Reducir animaciones</label>
      <p class="setting-description">Minimiza las animaciones y transiciones para mejorar la accesibilidad</p>
    </div>
    <div class="setting-control">
      <ToggleSwitch
        :model-value="themeStore.config.reducedMotion"
        @update:model-value="onReducedMotionChange"
      />
    </div>
  </div>

  <!-- Botón de restablecer apariencia -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Restablecer apariencia</label>
      <p class="setting-description">Volver a los valores por defecto de apariencia</p>
    </div>
    <div class="setting-control">
      <Button
        label="Restablecer"
        icon="pi pi-refresh"
        severity="secondary"
        outlined
        size="small"
        @click="themeStore.resetToDefaults()"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import {
  useThemeStore,
  PRIMARY_COLORS,
  FONT_SIZES,
  LINE_HEIGHTS,
  UI_RADIUS,
  UI_COMPACTNESS,
  FONT_FAMILIES,
  PRESETS,
  type ThemePreset,
  type LineHeight,
  type FontFamily
} from '@/stores/theme'

const themeStore = useThemeStore()

// ============================================================================
// Opciones de apariencia
// ============================================================================

const modeOptions = [
  { label: 'Claro', value: 'light' },
  { label: 'Oscuro', value: 'dark' },
  { label: 'Auto', value: 'auto' }
]

// Construir opciones de preset desde el store con categorías
interface PresetOption {
  label: string
  value: ThemePreset
  description: string
  category: 'general' | 'writing'
}

const presetOptions = computed<PresetOption[]>(() => {
  return Object.entries(PRESETS).map(([key, info]) => ({
    label: info.name,
    value: key as ThemePreset,
    description: info.description,
    category: info.category
  }))
})

// Agrupar presets por categoría para el dropdown
const groupedPresetOptions = computed(() => {
  const categories = {
    general: { label: 'Generales', items: [] as PresetOption[] },
    writing: { label: 'Para escritura', items: [] as PresetOption[] }
  }

  for (const preset of presetOptions.value) {
    categories[preset.category].items.push(preset)
  }

  return Object.values(categories).filter(cat => cat.items.length > 0)
})

const fontSizeOptions = Object.entries(FONT_SIZES).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

const lineHeightOptions = Object.entries(LINE_HEIGHTS).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

const radiusOptions = Object.entries(UI_RADIUS).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

const compactnessOptions = Object.entries(UI_COMPACTNESS).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

// Opciones de fuentes agrupadas por categoría
interface FontOption {
  label: string
  value: FontFamily
  description: string
  category: 'general' | 'reading'
}

const fontOptions = computed<FontOption[]>(() => {
  return Object.entries(FONT_FAMILIES).map(([key, info]) => ({
    label: info.label,
    value: key as FontFamily,
    description: info.description,
    category: info.category
  }))
})

const groupedFontOptions = computed(() => {
  const categories = {
    general: { label: 'Generales', items: [] as FontOption[] },
    reading: { label: 'Para lectura', items: [] as FontOption[] }
  }

  for (const font of fontOptions.value) {
    categories[font.category].items.push(font)
  }

  return Object.values(categories).filter(cat => cat.items.length > 0)
})

// ============================================================================
// Helper functions
// ============================================================================

const getPresetName = (value: string): string => {
  return PRESETS[value as ThemePreset]?.name ?? value
}

const getFontFamilyLabel = (value: string): string => {
  return FONT_FAMILIES[value as FontFamily]?.label ?? value
}

const getCategoryIcon = (categoryLabel: string): string => {
  const icons: Record<string, string> = {
    'Generales': 'pi pi-palette',
    'Para escritura': 'pi pi-pencil'
  }
  return icons[categoryLabel] || 'pi pi-circle'
}

// ============================================================================
// Handlers para controles de apariencia
// ============================================================================

const onPresetChange = (val: ThemePreset) => {
  themeStore.setPreset(val)
}

const onLineHeightChange = (val: LineHeight) => {
  themeStore.setLineHeight(val)
}

const onFontFamilyChange = (val: FontFamily) => {
  themeStore.setFontFamily(val)
}

const onFontFamilyReadingChange = (val: FontFamily) => {
  themeStore.setFontFamilyReading(val)
}

const onReducedMotionChange = (val: boolean) => {
  themeStore.setReducedMotion(val)
}
</script>

<style scoped>
/* ============================================================================
   Layout compartido con SettingsView (setting-item, setting-info, etc.)
   Necesario porque el componente hijo tiene scoped styles independientes
   ============================================================================ */

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 0;
  border-bottom: 1px solid var(--p-surface-200);
}

:global(.dark) .setting-item {
  border-bottom-color: var(--p-surface-700);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  flex: 1;
  padding-right: 2rem;
}

.setting-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--p-text-color);
}

.setting-description {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.setting-control {
  min-width: 200px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.setting-control.wide {
  min-width: 350px;
}

/* ============================================================================
   Paleta de colores
   ============================================================================ */

.color-palette {
  display: grid;
  grid-template-columns: repeat(6, 32px);
  gap: 0.5rem;
  justify-content: flex-end;
}

.color-swatch {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  padding: 0;
  outline: none;
}

.color-swatch:hover {
  transform: scale(1.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.color-swatch.active {
  border-color: var(--p-text-color);
  transform: scale(1.1);
  box-shadow: 0 0 0 2px var(--p-surface-0), 0 0 0 4px var(--p-text-color);
}

.color-swatch i {
  color: white;
  font-size: 0.75rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* Dark mode ajustes para color swatches */
.dark .color-swatch.active {
  box-shadow: 0 0 0 2px var(--p-surface-900), 0 0 0 4px var(--p-text-color);
}

/* ============================================================================
   Preset selector styles
   ============================================================================ */

.preset-dropdown {
  width: 100%;
  min-width: 280px;
}

.preset-selected {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.preset-group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.preset-group-header i {
  font-size: 0.9rem;
}

.preset-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0.25rem;
  width: 100%;
}

.preset-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  flex: 1;
}

.preset-name {
  font-weight: 500;
}

.preset-desc {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

/* ============================================================================
   Font selector styles
   ============================================================================ */

.font-dropdown {
  width: 100%;
  min-width: 280px;
}

.font-group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.font-group-header i {
  font-size: 0.9rem;
}

.font-option {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.font-name {
  font-weight: 500;
}

.font-desc {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

/* Clases de fuente para previsualización */
/* Generales */
.font-system { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.font-inter { font-family: 'Inter', sans-serif; }
.font-source-sans { font-family: 'Source Sans 3', sans-serif; }
.font-nunito { font-family: 'Nunito', sans-serif; }
/* Lectura modernas */
.font-literata { font-family: 'Literata', Georgia, serif; }
.font-merriweather { font-family: 'Merriweather', Georgia, serif; }
.font-source-serif { font-family: 'Source Serif 4', Georgia, serif; }
.font-lora { font-family: 'Lora', Georgia, serif; }
/* Clásicas */
.font-garamond { font-family: 'EB Garamond', Garamond, serif; }
.font-baskerville { font-family: 'Libre Baskerville', Baskerville, serif; }
.font-crimson { font-family: 'Crimson Pro', serif; }
.font-playfair { font-family: 'Playfair Display', serif; }
.font-pt-serif { font-family: 'PT Serif', serif; }
.font-cormorant { font-family: 'Cormorant Garamond', Garamond, serif; }
.font-ibm-plex-serif { font-family: 'IBM Plex Serif', serif; }
.font-spectral { font-family: 'Spectral', serif; }
/* Accesibles y especializadas */
.font-atkinson { font-family: 'Atkinson Hyperlegible', sans-serif; }
.font-roboto-serif { font-family: 'Roboto Serif', serif; }
.font-noto-serif { font-family: 'Noto Serif', serif; }
.font-caslon { font-family: 'Libre Caslon Text', serif; }

/* Aumentar el tamaño de fuente en las previsualizaciones del selector para que se vea bien */
.font-option .font-name {
  font-size: 1.1rem;
}

/* ============================================================================
   Grid 2-col para controles compactos (font size, line height, radius, density)
   ============================================================================ */

.compact-settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 0;
  border-bottom: 1px solid var(--p-surface-200);
}

:global(.dark) .compact-settings-grid {
  border-bottom-color: var(--p-surface-700);
}

.compact-settings-grid .setting-item {
  border-bottom: none;
  border-right: 1px solid var(--p-surface-200);
  padding-right: 1.25rem;
}

:global(.dark) .compact-settings-grid .setting-item {
  border-right-color: var(--p-surface-700);
}

/* Right column items: left padding from divider, no right border */
.compact-settings-grid .setting-item:nth-child(2n) {
  border-right: none;
  padding-left: 1.25rem;
  padding-right: 0;
}

/* Single column: remove all right borders */
@media (max-width: 900px) {
  .compact-settings-grid {
    grid-template-columns: 1fr;
  }
  .compact-settings-grid .setting-item {
    border-right: none;
    border-bottom: 1px solid var(--p-surface-200);
    padding-left: 0;
    padding-right: 0;
  }
  :global(.dark) .compact-settings-grid .setting-item {
    border-bottom-color: var(--p-surface-700);
  }
  .compact-settings-grid .setting-item:last-child {
    border-bottom: none;
  }
}
</style>
