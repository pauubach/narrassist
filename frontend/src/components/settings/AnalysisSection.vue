<template>
  <!-- Sensibilidad del análisis - Control unificado -->
  <div class="sensitivity-section">
    <div class="sensitivity-header">
      <label class="setting-label">¿Cuántas sugerencias quieres ver?</label>
      <p class="setting-description">
        Ajusta cuánto debería avisarte el asistente
      </p>
    </div>

    <!-- Presets como botones (2x2 en pantallas anchas) -->
    <div class="sensitivity-presets-grid">
      <button
        v-for="preset in sensitivity.sensitivityPresets"
        :key="preset.value"
        class="preset-button"
        :class="{ active: ctx.settings.value.sensitivityPreset === preset.value }"
        @click="sensitivity.selectSensitivityPreset(preset.value)"
      >
        <i :class="preset.icon"></i>
        <div class="preset-content">
          <span class="preset-title">{{ preset.label }}</span>
          <span class="preset-desc">{{ preset.description }}</span>
        </div>
        <i v-if="preset.recommended" class="pi pi-star-fill recommended-star" title="Recomendado"></i>
      </button>
    </div>

    <!-- Slider de ajuste fino (siempre visible pero con etiqueta contextual) -->
    <div class="sensitivity-slider">
      <div class="slider-header">
        <span class="slider-label">Ajuste fino</span>
        <span class="slider-value">{{ sensitivity.sensitivityLabel.value }}</span>
      </div>
      <Slider
        v-model="ctx.settings.value.sensitivity"
        :min="0"
        :max="100"
        :step="5"
        aria-label="Ajuste fino de sensibilidad"
        @change="sensitivity.onSensitivityChange"
      />
      <div class="slider-hints">
        <span>Menos avisos</span>
        <span>Más avisos</span>
      </div>
    </div>

    <!-- Panel avanzado colapsable -->
    <div class="advanced-panel">
      <button
        class="advanced-toggle"
        @click="sensitivity.showAdvancedSensitivity.value = !sensitivity.showAdvancedSensitivity.value"
      >
        <i :class="sensitivity.showAdvancedSensitivity.value ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
        <span>Opciones avanzadas</span>
      </button>

      <div v-if="sensitivity.showAdvancedSensitivity.value" class="advanced-content">
        <p class="advanced-note">
          Estos valores se calculan automáticamente según la sensibilidad elegida.
          Solo modifícalos si necesitas control preciso.
        </p>

        <div class="advanced-slider">
          <div class="advanced-slider-header">
            <label>Certeza para mostrar alertas</label>
            <span>{{ ctx.settings.value.minConfidence }}%</span>
          </div>
          <p class="slider-help">Qué tan seguro debe estar el sistema para mostrarte una alerta. Más bajo = más alertas (algunas pueden ser falsas).</p>
          <Slider
            v-model="ctx.settings.value.minConfidence"
            :min="20"
            :max="95"
            :step="5"
            aria-label="Certeza para mostrar alertas"
            @change="sensitivity.onAdvancedSliderChange"
          />
        </div>

        <div class="advanced-slider">
          <div class="advanced-slider-header">
            <label>Certeza para detectar personajes</label>
            <span>{{ ctx.settings.value.inferenceMinConfidence }}%</span>
          </div>
          <p class="slider-help">Qué tan seguro debe estar para identificar que dos menciones son el mismo personaje.</p>
          <Slider
            v-model="ctx.settings.value.inferenceMinConfidence"
            :min="20"
            :max="90"
            :step="5"
            aria-label="Certeza para detectar personajes"
            @change="sensitivity.onAdvancedSliderChange"
          />
        </div>

        <div class="advanced-slider">
          <div class="advanced-slider-header">
            <label>Acuerdo entre métodos</label>
            <span>{{ ctx.settings.value.inferenceMinConsensus }}%</span>
          </div>
          <p class="slider-help">Cuántos métodos deben coincidir para aceptar una detección. Más alto = más fiable pero puede perder algunas.</p>
          <Slider
            v-model="ctx.settings.value.inferenceMinConsensus"
            :min="30"
            :max="100"
            :step="10"
            aria-label="Acuerdo entre métodos"
            @change="sensitivity.onAdvancedSliderChange"
          />
        </div>

        <Button
          label="Restaurar valores calculados"
          icon="pi pi-refresh"
          severity="secondary"
          text
          size="small"
          @click="sensitivity.recalculateFromSensitivity"
        />
      </div>
    </div>
  </div>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Análisis automático</label>
      <p class="setting-description">Iniciar análisis automáticamente al crear proyecto</p>
    </div>
    <div class="setting-control">
      <ToggleSwitch
        v-model="ctx.settings.value.autoAnalysis"
        inputId="settings-auto-analysis"
        aria-label="Análisis automático"
        @change="ctx.onSettingChange"
      />
    </div>
  </div>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Mostrar resultados parciales</label>
      <p class="setting-description">Mostrar resultados disponibles mientras el análisis continúa</p>
    </div>
    <div class="setting-control">
      <ToggleSwitch
        v-model="ctx.settings.value.showPartialResults"
        inputId="settings-show-partial-results"
        aria-label="Mostrar resultados parciales"
        @change="ctx.onSettingChange"
      />
    </div>
  </div>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Notificaciones de análisis</label>
      <p class="setting-description">Notificar cuando el análisis se complete</p>
    </div>
    <div class="setting-control">
      <ToggleSwitch
        v-model="ctx.settings.value.notifyAnalysisComplete"
        inputId="settings-notify-analysis"
        aria-label="Notificaciones de análisis"
        @change="ctx.onSettingChange"
      />
    </div>
  </div>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Sonidos</label>
      <p class="setting-description">Reproducir sonidos para eventos importantes</p>
    </div>
    <div class="setting-control">
      <ToggleSwitch
        v-model="ctx.settings.value.soundEnabled"
        inputId="settings-sounds"
        aria-label="Sonidos"
        @change="ctx.onSettingChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import Slider from 'primevue/slider'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import { settingsKey, sensitivityKey } from './settingsInjection'

const ctx = inject(settingsKey)!
const sensitivity = inject(sensitivityKey)!
</script>
