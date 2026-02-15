<template>
  <div class="settings-view">
    <div class="settings-header">
      <Button
        icon="pi pi-arrow-left"
        text
        label="Volver"
        @click="goBack"
      />
      <h1>Configuración</h1>
    </div>

    <div class="settings-layout">
      <!-- Sidebar Navigation -->
      <nav class="settings-sidebar">
        <ul class="nav-menu">
          <li>
            <a href="#apariencia" :class="{ active: activeSection === 'apariencia' }" @click.prevent="scrollToSection('apariencia')">
              <i class="pi pi-palette"></i>
              <span>Apariencia</span>
            </a>
          </li>
          <li>
            <a href="#analisis" :class="{ active: activeSection === 'analisis' }" @click.prevent="scrollToSection('analisis')">
              <i class="pi pi-cog"></i>
              <span>Análisis</span>
            </a>
          </li>
          <li>
            <a href="#metodos-nlp" :class="{ active: activeSection === 'metodos-nlp' }" @click.prevent="scrollToSection('metodos-nlp')">
              <i class="pi pi-sliders-h"></i>
              <span>Métodos de Análisis</span>
            </a>
          </li>
          <li>
            <a href="#notificaciones" :class="{ active: activeSection === 'notificaciones' }" @click.prevent="scrollToSection('notificaciones')">
              <i class="pi pi-bell"></i>
              <span>Notificaciones</span>
            </a>
          </li>
          <li>
            <a href="#privacidad" :class="{ active: activeSection === 'privacidad' }" @click.prevent="scrollToSection('privacidad')">
              <i class="pi pi-shield"></i>
              <span>Privacidad</span>
            </a>
          </li>
          <li>
            <a href="#correcciones" :class="{ active: activeSection === 'correcciones' }" @click.prevent="scrollToSection('correcciones')">
              <i class="pi pi-pencil"></i>
              <span>Correcciones</span>
            </a>
          </li>
          <li>
            <a href="#mantenimiento" :class="{ active: activeSection === 'mantenimiento' }" @click.prevent="scrollToSection('mantenimiento')">
              <i class="pi pi-wrench"></i>
              <span>Mantenimiento</span>
            </a>
          </li>
        </ul>
      </nav>

      <!-- Content Area -->
      <div ref="contentArea" class="settings-content" @scroll="handleScroll">
        <!-- Apariencia -->
        <Card id="apariencia">
          <template #title>
            <div class="section-title">
              <i class="pi pi-palette"></i>
              <span>Apariencia</span>
            </div>
          </template>
          <template #content>
            <AppearanceSection />
          </template>
        </Card>

        <!-- Análisis -->
        <Card id="analisis">
          <template #title>
            <div class="section-title">
              <i class="pi pi-cog"></i>
              <span>Análisis</span>
            </div>
          </template>
          <template #content>
            <!-- Sensibilidad del análisis - Control unificado -->
            <div class="sensitivity-section">
              <div class="sensitivity-header">
                <label class="setting-label">¿Cuántas sugerencias quieres ver?</label>
                <p class="setting-description">
                  Ajusta cuánto debería avisarte el asistente
                </p>
              </div>

              <!-- Presets como botones -->
              <div class="sensitivity-presets">
                <button
                  v-for="preset in sensitivityPresets"
                  :key="preset.value"
                  class="preset-button"
                  :class="{ active: settings.sensitivityPreset === preset.value }"
                  @click="selectSensitivityPreset(preset.value)"
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
                  <span class="slider-value">{{ sensitivityLabel }}</span>
                </div>
                <Slider
                  v-model="settings.sensitivity"
                  :min="0"
                  :max="100"
                  :step="5"
                  @change="onSensitivityChange"
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
                  @click="showAdvancedSensitivity = !showAdvancedSensitivity"
                >
                  <i :class="showAdvancedSensitivity ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                  <span>Opciones avanzadas</span>
                </button>

                <div v-if="showAdvancedSensitivity" class="advanced-content">
                  <p class="advanced-note">
                    Estos valores se calculan automáticamente según la sensibilidad elegida.
                    Solo modifícalos si necesitas control preciso.
                  </p>

                  <div class="advanced-slider">
                    <div class="advanced-slider-header">
                      <label>Certeza para mostrar alertas</label>
                      <span>{{ settings.minConfidence }}%</span>
                    </div>
                    <p class="slider-help">Qué tan seguro debe estar el sistema para mostrarte una alerta. Más bajo = más alertas (algunas pueden ser falsas).</p>
                    <Slider
                      v-model="settings.minConfidence"
                      :min="20"
                      :max="95"
                      :step="5"
                      @change="onAdvancedSliderChange"
                    />
                  </div>

                  <div class="advanced-slider">
                    <div class="advanced-slider-header">
                      <label>Certeza para detectar personajes</label>
                      <span>{{ settings.inferenceMinConfidence }}%</span>
                    </div>
                    <p class="slider-help">Qué tan seguro debe estar para identificar que dos menciones son el mismo personaje.</p>
                    <Slider
                      v-model="settings.inferenceMinConfidence"
                      :min="20"
                      :max="90"
                      :step="5"
                      @change="onAdvancedSliderChange"
                    />
                  </div>

                  <div class="advanced-slider">
                    <div class="advanced-slider-header">
                      <label>Acuerdo entre métodos</label>
                      <span>{{ settings.inferenceMinConsensus }}%</span>
                    </div>
                    <p class="slider-help">Cuántos métodos deben coincidir para aceptar una detección. Más alto = más fiable pero puede perder algunas.</p>
                    <Slider
                      v-model="settings.inferenceMinConsensus"
                      :min="30"
                      :max="100"
                      :step="10"
                      @change="onAdvancedSliderChange"
                    />
                  </div>

                  <Button
                    label="Restaurar valores calculados"
                    icon="pi pi-refresh"
                    severity="secondary"
                    text
                    size="small"
                    @click="recalculateFromSensitivity"
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
                  v-model="settings.autoAnalysis"
                  @change="onSettingChange"
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
                  v-model="settings.showPartialResults"
                  @change="onSettingChange"
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- Métodos de Análisis -->
        <Card id="metodos-nlp">
          <template #title>
            <div class="section-title">
              <i class="pi pi-sliders-h"></i>
              <span>Métodos de Análisis</span>
              <Tag v-if="loadingCapabilities" value="Cargando..." severity="info" />
            </div>
          </template>
          <template #content>
            <!-- 1. Hardware Info Banner (CPU/GPU) -->
            <Message
              v-if="systemCapabilities"
              :severity="systemCapabilities.hardware.has_gpu ? 'success' : systemCapabilities.hardware.gpu_blocked ? 'warn' : 'info'"
              :closable="false"
              class="hardware-banner"
            >
              <div class="hardware-info">
                <i :class="systemCapabilities.hardware.has_gpu ? 'pi pi-bolt' : systemCapabilities.hardware.gpu_blocked ? 'pi pi-exclamation-triangle' : 'pi pi-desktop'"></i>
                <div>
                  <template v-if="systemCapabilities.hardware.has_gpu">
                    <strong>Aceleración por hardware detectada</strong>
                    <span>
                      - {{ systemCapabilities.hardware.gpu?.name }}
                      <template v-if="systemCapabilities.hardware.gpu?.memory_gb">
                        ({{ systemCapabilities.hardware.gpu?.memory_gb.toFixed(1) }} GB)
                      </template>
                    </span>
                  </template>
                  <template v-else-if="systemCapabilities.hardware.gpu_blocked">
                    <strong>Hardware no compatible</strong>
                    <span>
                      - {{ systemCapabilities.hardware.gpu_blocked.name }}
                      no es compatible con el análisis avanzado
                      (Compute Capability {{ systemCapabilities.hardware.gpu_blocked.compute_capability }},
                      se requiere {{ systemCapabilities.hardware.gpu_blocked.min_required }}+).
                      Usando CPU.
                    </span>
                  </template>
                  <template v-else>
                    <strong>Modo CPU</strong>
                    <span>- {{ systemCapabilities.hardware.cpu.name }}</span>
                  </template>
                </div>
              </div>
            </Message>

            <!-- 2. Analizador Semántico -->
            <div class="nlp-category">
              <div class="category-header">
                <h4><i class="pi pi-microchip-ai"></i> Analizador Semántico</h4>
                <span class="category-desc">Análisis avanzado del significado y contexto</span>
              </div>

              <!-- Estado del analizador compacto cuando está listo -->
              <div v-if="systemCapabilities && ollamaState === 'ready'" class="ollama-ready-bar">
                <div class="ollama-ready-info">
                  <i class="pi pi-check-circle"></i>
                  <span>Analizador listo · {{ systemCapabilities.ollama.models.length }} modelo(s)</span>
                </div>
              </div>

              <!-- Banner de acción cuando el analizador NO está listo -->
              <div v-if="systemCapabilities && ollamaState !== 'ready'" class="ollama-action-card" :class="'ollama-state-' + ollamaState">
                <div class="ollama-action-content">
                  <i
                    :class="[
                      ollamaState === 'no_models' ? 'pi pi-info-circle' : 'pi pi-exclamation-triangle'
                    ]"
                  ></i>
                  <div class="ollama-action-text">
                    <strong>{{
                      ollamaState === 'not_installed' ? 'Analizador no disponible' :
                      ollamaState === 'not_running' ? 'Analizador no iniciado' :
                      'Sin modelos de análisis'
                    }}</strong>
                    <span>{{ ollamaStatusMessage }}</span>
                  </div>
                  <Button
                    v-if="!modelDownloading"
                    :label="ollamaActionConfig.label"
                    :icon="ollamaActionConfig.icon"
                    :severity="ollamaActionConfig.severity"
                    size="small"
                    :loading="ollamaStarting"
                    @click="ollamaActionConfig.action"
                  />
                </div>
                <!-- Barra de progreso de descarga de modelo -->
                <DsDownloadProgress
                  v-if="modelDownloading"
                  label="Descargando modelo de IA..."
                  :percentage="ollamaDownloadProgress?.percentage ?? null"
                  class="ollama-progress-wrapper"
                />
              </div>

              <!-- Selector de modelos -->
              <div class="setting-item" :class="{ 'setting-disabled': ollamaState !== 'ready' }">
                <div class="setting-info">
                  <label class="setting-label">Modelos de análisis</label>
                  <p class="setting-description">
                    Selecciona qué modelos usar para el análisis semántico.
                  </p>
                </div>
                <div class="setting-control wide">
                  <MultiSelect
                    v-model="settings.enabledInferenceMethods"
                    :options="availableLLMOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Seleccionar modelos"
                    display="chip"
                    :show-toggle-all="false"
                    :disabled="ollamaState !== 'ready'"
                    @change="onSettingChange"
                  >
                    <template #option="slotProps">
                      <div class="method-option">
                        <div class="method-info">
                          <span class="method-name">{{ slotProps.option.label }}</span>
                          <span class="method-desc">{{ slotProps.option.description }}</span>
                        </div>
                        <div class="method-badges">
                          <Badge
                            :value="getSpeedLabel(slotProps.option.speed)"
                            :severity="getSpeedSeverity(slotProps.option.speed)"
                            class="speed-badge"
                          />
                          <Tag
                            v-if="!slotProps.option.installed"
                            value="No instalado"
                            severity="warning"
                            class="method-tag"
                          />
                        </div>
                      </div>
                    </template>
                  </MultiSelect>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <label class="setting-label">Priorizar velocidad</label>
                  <p class="setting-description">
                    Usar configuración optimizada para respuestas rápidas sobre calidad
                  </p>
                </div>
                <div class="setting-control">
                  <ToggleSwitch
                    v-model="settings.prioritizeSpeed"
                    :disabled="ollamaState !== 'ready'"
                    @change="onSettingChange"
                  />
                </div>
              </div>
            </div>

            <!-- 3. Correferencia -->
            <div class="nlp-category">
              <div class="category-header">
                <h4><i class="pi pi-link"></i> Seguimiento de referencias</h4>
                <span class="category-desc">Detecta cuándo "él", "la detective" o "María" se refieren al mismo personaje</span>
              </div>
              <div class="methods-grid">
                <div
                  v-for="(method, key) in getNLPMethodsForCategory('coreference')"
                  :key="key"
                  class="method-card"
                  :class="{ disabled: !method.available, enabled: isMethodEnabled('coreference', String(key)) }"
                >
                  <div class="method-header">
                    <ToggleSwitch
                      :model-value="isMethodEnabled('coreference', String(key))"
                      :disabled="!method.available"
                      @update:model-value="toggleMethod('coreference', String(key), $event)"
                    />
                    <span class="method-name">{{ method.name }}</span>
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
                    <Tag
                      v-if="method.requires_gpu"
                      v-tooltip.top="gpuRequirementTooltip"
                      :value="systemCapabilities?.hardware.gpu_blocked ? 'Hardware no compatible' : 'Requiere aceleración'"
                      severity="warning"
                      class="method-tag"
                    />
                    <Tag v-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
                  </div>
                  <p class="method-description">{{ method.description }}</p>
                  <div v-if="method.weight" class="method-weight">
                    Peso en votación: {{ (method.weight * 100).toFixed(0) }}%
                  </div>
                </div>
              </div>
            </div>

            <!-- 4. NER -->
            <div class="nlp-category">
              <div class="category-header">
                <h4><i class="pi pi-user"></i> Detección de personajes y lugares</h4>
                <span class="category-desc">Identifica automáticamente nombres de personas, lugares y organizaciones</span>
              </div>
              <div class="methods-grid">
                <div
                  v-for="(method, key) in getNLPMethodsForCategory('ner')"
                  :key="key"
                  class="method-card"
                  :class="{ disabled: !method.available, enabled: isMethodEnabled('ner', String(key)) }"
                >
                  <div class="method-header">
                    <ToggleSwitch
                      :model-value="isMethodEnabled('ner', String(key))"
                      :disabled="!method.available"
                      @update:model-value="toggleMethod('ner', String(key), $event)"
                    />
                    <span class="method-name">{{ method.name }}</span>
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
                    <Tag
                      v-if="method.requires_gpu"
                      v-tooltip.top="gpuRequirementTooltip"
                      :value="systemCapabilities?.hardware.gpu_blocked ? 'Hardware no compatible' : 'Requiere aceleración'"
                      severity="warning"
                      class="method-tag"
                    />
                    <Tag v-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
                  </div>
                  <p class="method-description">{{ method.description }}</p>
                </div>
              </div>
            </div>

            <!-- 5. Gramática -->
            <div class="nlp-category">
              <div class="category-header">
                <h4><i class="pi pi-check-circle"></i> Corrección gramatical</h4>
                <span class="category-desc">Detecta errores de concordancia, puntuación y otros problemas gramaticales</span>
              </div>

              <!-- LanguageTool status bar -->
              <div v-if="ltState === 'running'" class="ollama-ready-bar" style="margin-bottom: 0.75rem;">
                <div class="ollama-ready-info">
                  <i class="pi pi-check-circle"></i>
                  <span>Corrector avanzado activo (LanguageTool · +2000 reglas)</span>
                </div>
              </div>
              <div v-else class="ollama-action-card" :class="'ollama-state-' + (ltState === 'not_installed' ? 'not_installed' : ltState === 'installing' ? 'no_models' : 'not_running')" style="margin-bottom: 0.75rem;">
                <div class="ollama-action-content">
                  <i v-if="ltState !== 'installing'" class="pi pi-exclamation-triangle"></i>
                  <i v-else class="pi pi-download"></i>
                  <div class="ollama-action-text" style="flex: 1;">
                    <strong>{{
                      ltState === 'not_installed' ? 'Corrector avanzado no disponible' :
                      ltState === 'installing' ? 'Instalando corrector avanzado' :
                      'Corrector avanzado no iniciado'
                    }}</strong>
                    <span>{{ ltStatusMessage }}</span>
                    <!-- Barra de progreso para instalación -->
                    <DsDownloadProgress
                      v-if="ltState === 'installing' && ltInstallProgress"
                      :label="ltInstallProgress.phase_label"
                      :percentage="ltInstallProgress.percentage > 0 ? ltInstallProgress.percentage : null"
                      :detail="ltInstallProgress.detail"
                      class="lt-progress-container"
                    />
                  </div>
                  <Button
                    v-if="ltState !== 'installing'"
                    :label="ltActionConfig.label"
                    :icon="ltActionConfig.icon"
                    :severity="ltActionConfig.severity"
                    size="small"
                    :loading="ltInstalling || ltStarting"
                    @click="ltActionConfig.action"
                  />
                </div>
              </div>

              <div class="methods-grid">
                <div
                  v-for="(method, key) in getNLPMethodsForCategory('grammar')"
                  :key="key"
                  class="method-card"
                  :class="{ disabled: !method.available, enabled: isMethodEnabled('grammar', String(key)) }"
                >
                  <div class="method-header">
                    <ToggleSwitch
                      :model-value="isMethodEnabled('grammar', String(key))"
                      :disabled="!method.available"
                      @update:model-value="toggleMethod('grammar', String(key), $event)"
                    />
                    <span class="method-name">{{ method.name }}</span>
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
                    <Tag
                      v-if="method.requires_gpu"
                      v-tooltip.top="gpuRequirementTooltip"
                      :value="systemCapabilities?.hardware.gpu_blocked ? 'Hardware no compatible' : 'Requiere aceleración'"
                      severity="warning"
                      class="method-tag"
                    />
                    <Tag v-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
                  </div>
                  <p class="method-description">{{ method.description }}</p>
                </div>
              </div>
            </div>

            <!-- 6. Ortografía (Votación Multi-Método) -->
            <div class="nlp-category">
              <div class="category-header">
                <h4><i class="pi pi-spell-check"></i> Corrección ortográfica</h4>
                <span class="category-desc">Sistema de votación con múltiples correctores para máxima precisión</span>
              </div>
              <div class="methods-grid">
                <div
                  v-for="(method, key) in getNLPMethodsForCategory('spelling')"
                  :key="key"
                  class="method-card"
                  :class="{ disabled: !method.available, enabled: isMethodEnabled('spelling', String(key)) }"
                >
                  <div class="method-header">
                    <ToggleSwitch
                      :model-value="isMethodEnabled('spelling', String(key))"
                      :disabled="!method.available"
                      @update:model-value="toggleMethod('spelling', String(key), $event)"
                    />
                    <span class="method-name">{{ method.name }}</span>
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
                    <Tag v-if="method.recommended_gpu && !method.requires_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
                    <Tag
                      v-if="method.requires_gpu"
                      v-tooltip.top="gpuRequirementTooltip"
                      :value="systemCapabilities?.hardware.gpu_blocked ? 'Hardware no compatible' : 'Requiere aceleración'"
                      severity="warning"
                      class="method-tag"
                    />
                    <Tag v-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
                  </div>
                  <p class="method-description">{{ method.description }}</p>
                  <div v-if="method.weight" class="method-weight">
                    Peso en votación: {{ (method.weight * 100).toFixed(0) }}%
                  </div>
                </div>
              </div>
            </div>

            <!-- 7. Conocimiento de Personajes -->
            <div class="nlp-category">
              <div class="category-header">
                <h4><i class="pi pi-book"></i> Conocimiento de personajes</h4>
                <span class="category-desc">Extrae qué sabe cada personaje sobre otros y sobre eventos</span>
              </div>
              <div class="knowledge-mode-selector">
                <div
                  v-for="(method, key) in getNLPMethodsForCategory('character_knowledge')"
                  :key="key"
                  class="knowledge-mode-card"
                  :class="{
                    disabled: !method.available,
                    selected: settings.characterKnowledgeMode === key
                  }"
                  @click="method.available && setCharacterKnowledgeMode(String(key))"
                >
                  <span class="mode-name">{{ method.name }}</span>
                  <p class="mode-description">{{ method.description }}</p>
                  <Tag v-if="method.recommended_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
                  <Tag v-if="method.recommended_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
                  <Tag v-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
                </div>
              </div>
            </div>

            <!-- Botón para aplicar configuración recomendada -->
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Configuración recomendada</label>
                <p class="setting-description">Aplicar configuración óptima según tu hardware detectado</p>
              </div>
              <div class="setting-control">
                <Button
                  label="Aplicar recomendada"
                  icon="pi pi-sparkles"
                  severity="secondary"
                  outlined
                  size="small"
                  :disabled="!systemCapabilities"
                  @click="applyRecommendedConfig"
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- Notificaciones -->
        <Card id="notificaciones">
          <template #title>
            <div class="section-title">
              <i class="pi pi-bell"></i>
              <span>Notificaciones</span>
            </div>
          </template>
          <template #content>
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Notificaciones de análisis</label>
                <p class="setting-description">Notificar cuando el análisis se complete</p>
              </div>
              <div class="setting-control">
                <ToggleSwitch
                  v-model="settings.notifyAnalysisComplete"
                  @change="onSettingChange"
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
                  v-model="settings.soundEnabled"
                  @change="onSettingChange"
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- Privacidad y Datos -->
        <Card id="privacidad">
          <template #title>
            <div class="section-title">
              <i class="pi pi-shield"></i>
              <span>Privacidad y Datos</span>
            </div>
          </template>
          <template #content>
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Ubicación de datos</label>
                <p class="setting-description">
                  Los proyectos se guardan en: <code>{{ dataLocation }}</code>
                </p>
              </div>
              <div class="setting-control">
                <Button
                  label="Cambiar ubicación"
                  icon="pi pi-folder-open"
                  outlined
                  @click="changeDataLocation"
                />
              </div>
            </div>

            <Message severity="info" :closable="false" class="info-message">
              <span class="message-content">
                <strong>Modo 100% offline:</strong> Tus manuscritos nunca salen de tu máquina.
                Esta aplicación no envía datos a internet excepto para verificación de licencia.
              </span>
            </Message>
          </template>
        </Card>

        <!-- Correcciones -->
        <Card id="correcciones">
          <template #title>
            <div class="section-title">
              <i class="pi pi-pencil"></i>
              <span>Correcciones Editoriales</span>
            </div>
          </template>
          <template #content>
            <!-- Nota informativa -->
            <Message severity="info" :closable="false" class="mb-4">
              <template #default>
                <div class="correction-info-message">
                  <p>
                    La configuración de correcciones se aplica por proyecto. Aquí puedes seleccionar un preset base
                    que se aplicará a nuevos proyectos. Para ajustar la configuración de un proyecto específico,
                    accede a sus ajustes desde el panel del proyecto.
                  </p>
                </div>
              </template>
            </Message>

            <!-- Preset para nuevos proyectos -->
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Preset por defecto</label>
                <p class="setting-description">
                  Configuración base que se aplicará a nuevos proyectos. Puedes personalizarla después.
                </p>
              </div>
              <div class="setting-control wide">
                <Select
                  v-model="defaultCorrectionPreset"
                  :options="correctionPresetOptions"
                  option-label="name"
                  option-value="id"
                  placeholder="Selecciona un preset"
                  class="w-full"
                  @change="onDefaultPresetChange"
                >
                  <template #option="slotProps">
                    <div class="preset-dropdown-option">
                      <span class="preset-name">{{ slotProps.option.name }}</span>
                      <span class="preset-description">{{ slotProps.option.description }}</span>
                    </div>
                  </template>
                </Select>
              </div>
            </div>

            <!-- Resumen de configuración actual -->
            <div v-if="defaultCorrectionConfig" class="setting-item column">
              <div class="setting-info">
                <label class="setting-label">Resumen de configuración</label>
                <p class="setting-description">
                  Vista previa de la configuración del preset seleccionado
                </p>
              </div>
              <div class="correction-config-summary">
                <div class="config-grid">
                  <!-- Perfil de documento -->
                  <div class="config-section">
                    <h4><i class="pi pi-file"></i> Perfil de documento</h4>
                    <div class="config-items">
                      <div class="config-item">
                        <span class="config-label">Tipo:</span>
                        <Tag :value="getFieldLabel(defaultCorrectionConfig.profile?.document_field)" severity="info" />
                      </div>
                      <div class="config-item">
                        <span class="config-label">Registro:</span>
                        <Tag :value="getRegisterLabel(defaultCorrectionConfig.profile?.register)" severity="secondary" />
                      </div>
                      <div class="config-item">
                        <span class="config-label">Audiencia:</span>
                        <span>{{ getAudienceLabel(defaultCorrectionConfig.profile?.audience) }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Tipografía -->
                  <div class="config-section">
                    <h4><i class="pi pi-align-left"></i> Tipografía</h4>
                    <div class="config-items">
                      <div class="config-item">
                        <span class="config-label">Habilitado:</span>
                        <i :class="defaultCorrectionConfig.typography?.enabled ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
                      </div>
                      <div class="config-item">
                        <span class="config-label">Guiones:</span>
                        <span>{{ getDashLabel(defaultCorrectionConfig.typography?.dialogue_dash) }}</span>
                      </div>
                      <div class="config-item">
                        <span class="config-label">Comillas:</span>
                        <span>{{ getQuoteLabel(defaultCorrectionConfig.typography?.quote_style) }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Repeticiones -->
                  <div class="config-section">
                    <h4><i class="pi pi-copy"></i> Repeticiones</h4>
                    <div class="config-items">
                      <div class="config-item">
                        <span class="config-label">Habilitado:</span>
                        <i :class="defaultCorrectionConfig.repetition?.enabled ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
                      </div>
                      <div class="config-item">
                        <span class="config-label">Distancia mín:</span>
                        <span>{{ defaultCorrectionConfig.repetition?.min_distance }} palabras</span>
                      </div>
                      <div class="config-item">
                        <span class="config-label">Sensibilidad:</span>
                        <Tag :value="getSensitivityLabel(defaultCorrectionConfig.repetition?.sensitivity)" :severity="getSensitivitySeverity(defaultCorrectionConfig.repetition?.sensitivity)" />
                      </div>
                    </div>
                  </div>

                  <!-- Regional -->
                  <div class="config-section">
                    <h4><i class="pi pi-globe"></i> Vocabulario regional</h4>
                    <div class="config-items">
                      <div class="config-item">
                        <span class="config-label">Habilitado:</span>
                        <i :class="defaultCorrectionConfig.regional?.enabled ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
                      </div>
                      <div class="config-item">
                        <span class="config-label">Región:</span>
                        <span>{{ getRegionLabel(defaultCorrectionConfig.regional?.target_region) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Variante regional por defecto -->
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Variante regional</label>
                <p class="setting-description">
                  Variante del español para nuevos proyectos. Cada proyecto puede personalizarse desde su configuración.
                </p>
              </div>
              <div class="setting-control">
                <Select
                  v-model="defaultRegion"
                  :options="regionOptions"
                  option-label="label"
                  option-value="value"
                  placeholder="Selecciona región"
                  @change="onDefaultRegionChange"
                />
              </div>
            </div>

            <!-- Revisión con LLM -->
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Revisión inteligente</label>
                <p class="setting-description">
                  Usar la IA para filtrar falsos positivos en las alertas de corrección.
                  Requiere el analizador semántico activo.
                </p>
              </div>
              <div class="setting-control">
                <ToggleSwitch v-model="useLLMReview" @change="onLLMReviewChange" />
              </div>
            </div>

            <Divider />

            <!-- Personalización de defaults por tipo -->
            <CorrectionDefaultsManager ref="defaultsManager" />
          </template>
        </Card>

        <!-- Acciones -->
        <Card id="mantenimiento">
          <template #title>
            <div class="section-title">
              <i class="pi pi-wrench"></i>
              <span>Mantenimiento</span>
            </div>
          </template>
          <template #content>
            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Modelos NLP</label>
                <p class="setting-description">Verificar y descargar modelos de análisis (spaCy, embeddings, NER)</p>
              </div>
              <div class="setting-control">
                <Button
                  :label="nlpDownloading ? 'Descargando...' : 'Verificar modelos'"
                  icon="pi pi-download"
                  severity="secondary"
                  outlined
                  :loading="nlpDownloading"
                  @click="redownloadNLPModels"
                />
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Limpiar caché</label>
                <p class="setting-description">Eliminar archivos temporales y caché de modelos</p>
              </div>
              <div class="setting-control">
                <Button
                  label="Limpiar caché"
                  icon="pi pi-trash"
                  severity="secondary"
                  outlined
                  @click="clearCache"
                />
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-info">
                <label class="setting-label">Restablecer configuración</label>
                <p class="setting-description">Volver a la configuración por defecto</p>
              </div>
              <div class="setting-control">
                <Button
                  label="Restablecer"
                  icon="pi pi-refresh"
                  severity="danger"
                  outlined
                  @click="confirmReset"
                />
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Confirm Reset Dialog -->
    <Dialog
      :visible="showResetDialog"
      modal
      header="Confirmar restablecimiento"
      :style="{ width: '450px' }"
      @update:visible="showResetDialog = $event"
    >
      <p>
        ¿Estás seguro de que deseas restablecer toda la configuración a los valores por defecto?
        Esta acción no se puede deshacer.
      </p>
      <template #footer>
        <Button label="Cancelar" severity="secondary" @click="showResetDialog = false" />
        <Button label="Restablecer" severity="danger" @click="resetSettings" />
      </template>
    </Dialog>

    <!-- Change Data Location Dialog -->
    <Dialog
      :visible="showDataLocationDialog"
      modal
      header="Cambiar ubicación de datos"
      :style="{ width: '550px' }"
      @update:visible="showDataLocationDialog = $event"
    >
      <div class="data-location-dialog">
        <p class="dialog-description">
          Selecciona una nueva carpeta donde se guardarán los proyectos y datos de la aplicación.
        </p>

        <div class="location-input">
          <label class="input-label">Nueva ubicación</label>
          <InputText
            v-model="newDataLocation"
            placeholder="Ej: C:\Users\Usuario\Documents\NarrativeAssistant"
            class="location-field"
          />
        </div>

        <div class="migrate-option">
          <ToggleSwitch v-model="migrateData" />
          <div class="migrate-info">
            <label>Migrar datos existentes</label>
            <span class="migrate-description">
              Copia los proyectos y configuración actual a la nueva ubicación
            </span>
          </div>
        </div>

        <Message severity="info" :closable="false" class="location-info-message">
          <span>Necesitarás reiniciar la aplicación después de cambiar la ubicación.</span>
        </Message>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          :disabled="changingLocation"
          @click="showDataLocationDialog = false"
        />
        <Button
          label="Cambiar ubicación"
          icon="pi pi-check"
          :loading="changingLocation"
          @click="confirmChangeDataLocation"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/apiClient'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Slider from 'primevue/slider'
import ToggleSwitch from 'primevue/toggleswitch'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import MultiSelect from 'primevue/multiselect'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import DsDownloadProgress from '@/components/ds/DsDownloadProgress.vue'
import Divider from 'primevue/divider'
import { useToast } from 'primevue/usetoast'
import CorrectionDefaultsManager from '@/components/settings/CorrectionDefaultsManager.vue'
import AppearanceSection from '@/components/settings/AppearanceSection.vue'
import { useSystemStore, type LTState } from '@/stores/system'
import type { CorrectionConfig } from '@/types'

// Composables
import { useSettingsPersistence } from '@/composables/useSettingsPersistence'
import { useSensitivityPresets } from '@/composables/useSensitivityPresets'
import { useOllamaManagement } from '@/composables/useOllamaManagement'
import { useNLPMethods } from '@/composables/useNLPMethods'
// Label utilities
import {
  getFieldLabel, getRegisterLabel, getAudienceLabel,
  getDashLabel, getQuoteLabel,
  getSensitivityLabel, getSensitivitySeverity,
  getRegionLabel, getSpeedLabel, getSpeedSeverity,
} from '@/utils/settingsLabels'
import { safeSetItem, safeGetItem } from '@/utils/safeStorage'

const router = useRouter()
const toast = useToast()
const systemStore = useSystemStore()

// ── Composable wiring ──────────────────────────────────────

const {
  settings, loadSettings, saveSettings, onSettingChange, onSliderChange,
  applyDefaultsFromCapabilities, resetSettings: doResetSettings, cleanup: cleanupPersistence,
} = useSettingsPersistence()

const {
  sensitivityPresets, showAdvancedSensitivity, sensitivityLabel,
  selectSensitivityPreset, onSensitivityChange, onAdvancedSliderChange, recalculateFromSensitivity,
} = useSensitivityPresets(settings, saveSettings, onSliderChange)

const {
  ollamaState, ollamaActionConfig, ollamaStatusMessage,
  ollamaStarting, modelDownloading, ollamaDownloadProgress,
  cleanup: cleanupOllama,
} = useOllamaManagement()

const {
  availableLLMOptions, gpuRequirementTooltip,
  getNLPMethodsForCategory, isMethodEnabled, toggleMethod,
  setCharacterKnowledgeMode, applyRecommendedConfig,
} = useNLPMethods(settings, saveSettings, applyDefaultsFromCapabilities)

// ── System capabilities (proxied from store) ───────────────

const systemCapabilities = computed(() => systemStore.systemCapabilities)
const loadingCapabilities = computed(() => systemStore.capabilitiesLoading)

// ── NLP model download ──────────────────────────────────────

const nlpDownloading = ref(false)

async function redownloadNLPModels() {
  nlpDownloading.value = true
  try {
    const ok = await systemStore.downloadModels(['spacy', 'embeddings', 'transformer_ner'])
    if (ok) {
      toast.add({ severity: 'success', summary: 'Modelos verificados', detail: 'Todos los modelos NLP están disponibles.', life: 3000 })
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: systemStore.modelsError || 'Error descargando modelos.', life: 5000 })
    }
  } finally {
    nlpDownloading.value = false
  }
}

// ── Data location state ────────────────────────────────────

const dataLocation = ref('~/.narrative_assistant')
const showResetDialog = ref(false)
const showDataLocationDialog = ref(false)
const newDataLocation = ref('')
const migrateData = ref(true)
const changingLocation = ref(false)

// ============================================================================
// Configuración de Correcciones
// ============================================================================

interface CorrectionPresetLocal {
  id: string
  name: string
  description: string
  config: CorrectionConfig
}

interface CorrectionOptions {
  document_fields: Array<{ value: string; label: string }>
  register_levels: Array<{ value: string; label: string }>
  audience_types: Array<{ value: string; label: string }>
  regions: Array<{ value: string; label: string }>
  quote_styles: Array<{ value: string; label: string }>
  dialogue_dashes: Array<{ value: string; label: string }>
  sensitivity_levels: Array<{ value: string; label: string }>
}

const correctionPresetOptions = ref<CorrectionPresetLocal[]>([])
const correctionOptions = ref<CorrectionOptions | null>(null)
const defaultCorrectionPreset = ref<string>('default')
const defaultCorrectionConfig = ref<CorrectionConfig | null>(null)
const defaultRegion = ref<string>('es_ES')
const useLLMReview = ref<boolean>(false)

const regionOptions = computed(() => correctionOptions.value?.regions || [
  { value: 'es_ES', label: 'Espana' },
  { value: 'es_MX', label: 'Mexico' },
  { value: 'es_AR', label: 'Argentina' },
  { value: 'es_CO', label: 'Colombia' },
])

// Cargar presets de correcciones
async function loadCorrectionPresets() {
  try {
    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>('/api/correction-presets')

    if (data.success && data.data) {
      correctionPresetOptions.value = data.data.presets || []
      correctionOptions.value = data.data.options || null

      // Cargar configuracion guardada
      const savedPreset = safeGetItem('defaultCorrectionPreset')
      if (savedPreset) {
        defaultCorrectionPreset.value = savedPreset
        const preset = correctionPresetOptions.value.find(p => p.id === savedPreset)
        if (preset) {
          defaultCorrectionConfig.value = preset.config
        }
      } else if (correctionPresetOptions.value.length > 0) {
        defaultCorrectionConfig.value = correctionPresetOptions.value[0].config
      }

      const savedRegion = safeGetItem('defaultCorrectionRegion')
      if (savedRegion) {
        defaultRegion.value = savedRegion
      }

      useLLMReview.value = safeGetItem('useLLMReview') === 'true'
    }
  } catch (error) {
    console.error('Error loading correction presets:', error)
  }
}

function onDefaultPresetChange() {
  const preset = correctionPresetOptions.value.find(p => p.id === defaultCorrectionPreset.value)
  if (preset) {
    defaultCorrectionConfig.value = preset.config
    safeSetItem('defaultCorrectionPreset', preset.id)
  }
}

function onDefaultRegionChange() {
  safeSetItem('defaultCorrectionRegion', defaultRegion.value)
}

function onLLMReviewChange() {
  safeSetItem('useLLMReview', useLLMReview.value.toString())
}

// LanguageTool state - usar store centralizado
const ltInstalling = computed(() => systemStore.ltInstalling)
const ltStarting = computed(() => systemStore.ltStarting)
const ltInstallProgress = computed(() => systemStore.ltInstallProgress)

const ltState = computed<LTState>(() => systemStore.ltState)

const ltActionConfig = computed(() => {
  const configs: Record<LTState, { label: string; icon: string; severity: string; action: () => void }> = {
    not_installed: {
      label: 'Instalar',
      icon: 'pi pi-download',
      severity: 'warning',
      action: installLanguageTool
    },
    installing: {
      label: 'Instalando...',
      icon: 'pi pi-spin pi-spinner',
      severity: 'info',
      action: () => {}
    },
    installed_not_running: {
      label: 'Iniciar',
      icon: 'pi pi-play',
      severity: 'warning',
      action: startLanguageTool
    },
    running: {
      label: 'Activo',
      icon: 'pi pi-check',
      severity: 'success',
      action: () => {}
    }
  }
  return configs[ltState.value]
})

const ltStatusMessage = computed(() => {
  // Si está instalando y tenemos progreso, mostrar el detalle
  if (ltState.value === 'installing' && ltInstallProgress.value) {
    return ltInstallProgress.value.detail || ltInstallProgress.value.phase_label
  }

  const messages: Record<LTState, string> = {
    not_installed: 'Instala el corrector avanzado para +2000 reglas de gramática y ortografía (~300MB)',
    installing: 'Iniciando descarga...',
    installed_not_running: 'Corrector avanzado instalado pero no activo',
    running: 'Corrector avanzado activo'
  }
  return messages[ltState.value]
})

// LanguageTool install/start - usar acciones del store con toasts
const installLanguageTool = async () => {
  toast.add({ severity: 'info', summary: 'Instalando corrector avanzado', detail: 'Descargando componentes necesarios...', life: 5000 })
  const success = await systemStore.installLanguageTool()
  if (success) {
    await loadSystemCapabilities()
    const lt = systemCapabilities.value?.languagetool
    if (lt?.running) {
      toast.add({ severity: 'success', summary: 'Corrector avanzado instalado', detail: 'Corrector avanzado disponible', life: 3000 })
    } else if (lt?.installed) {
      toast.add({ severity: 'success', summary: 'Corrector avanzado instalado', detail: 'Puedes iniciarlo desde aquí', life: 3000 })
    }
  } else {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo instalar el corrector avanzado', life: 5000 })
  }
}

const startLanguageTool = async () => {
  const success = await systemStore.startLanguageTool()
  if (success) {
    await loadSystemCapabilities()
    toast.add({ severity: 'success', summary: 'Corrector avanzado iniciado', detail: 'Corrector avanzado disponible', life: 3000 })
  } else {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo iniciar el corrector avanzado', life: 5000 })
  }
}

// Navigation
const activeSection = ref('apariencia')
const contentArea = ref<HTMLElement | null>(null)


onMounted(async () => {
  loadSettings()
  await loadSystemCapabilities()
  await loadCurrentDataLocation()
  await loadCorrectionPresets()
})

onUnmounted(() => {
  cleanupPersistence()
  cleanupOllama()
  systemStore.stopLTPolling()
})

const loadSystemCapabilities = async (): Promise<boolean> => {
  // Usar el store centralizado
  const capabilities = await systemStore.loadCapabilities(true) // force refresh
  if (capabilities) {
    // Si es la primera vez (no hay settings guardados), aplicar defaults según hardware
    const savedSettings = safeGetItem('narrative_assistant_settings')
    if (!savedSettings) {
      applyDefaultsFromCapabilities(capabilities)
    }
    return true
  }
  console.error('Error loading system capabilities')
  return false
}

const changeDataLocation = () => {
  // Cargar la ubicación actual
  loadCurrentDataLocation()
  showDataLocationDialog.value = true
}

const loadCurrentDataLocation = async () => {
  try {
    const result = await api.getRaw<{ success: boolean; data?: any }>('/api/maintenance/data-location')
    if (result.success && result.data) {
      dataLocation.value = result.data.path
      newDataLocation.value = result.data.path
    }
  } catch (error) {
    console.error('Error loading data location:', error)
  }
}

const confirmChangeDataLocation = async () => {
  if (!newDataLocation.value.trim()) {
    toast.add({
      severity: 'warn',
      summary: 'Ruta vacía',
      detail: 'Introduce una ruta válida',
      life: 3000
    })
    return
  }

  changingLocation.value = true

  try {
    const result = await api.postRaw<{ success: boolean; data?: any; error?: string }>('/api/maintenance/data-location', {
      new_path: newDataLocation.value,
      migrate_data: migrateData.value
    })

    if (result.success) {
      dataLocation.value = newDataLocation.value
      showDataLocationDialog.value = false

      toast.add({
        severity: 'success',
        summary: 'Ubicación actualizada',
        detail: result.data?.restart_required
          ? 'Reinicia la aplicación para aplicar los cambios'
          : 'La ubicación de datos ha sido actualizada',
        life: 5000
      })

      if (result.data?.migrated_items?.length > 0) {
        toast.add({
          severity: 'info',
          summary: 'Datos migrados',
          detail: `Se han migrado: ${result.data.migrated_items.join(', ')}`,
          life: 5000
        })
      }
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: result.error || 'No se pudo cambiar la ubicación',
        life: 5000
      })
    }
  } catch (error) {
    console.error('Error changing data location:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo completar la operación',
      life: 3000
    })
  } finally {
    changingLocation.value = false
  }
}

const clearCache = async () => {
  try {
    await api.postRaw('/api/maintenance/clear-cache')

    toast.add({
      severity: 'success',
      summary: 'Caché limpiado',
      detail: 'Los archivos temporales se han eliminado',
      life: 3000
    })
  } catch (error) {
    console.error('Error clearing cache:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo limpiar el caché',
      life: 3000
    })
  }
}

const confirmReset = () => {
  showResetDialog.value = true
}


const resetSettings = () => {
  doResetSettings(systemCapabilities.value)
  showResetDialog.value = false
}

const goBack = () => {
  router.go(-1)
}

const scrollToSection = (sectionId: string) => {
  const element = document.getElementById(sectionId)
  if (element && contentArea.value) {
    // Calcular la posición del elemento relativa al contenedor de scroll
    const containerRect = contentArea.value.getBoundingClientRect()
    const elementRect = element.getBoundingClientRect()

    // Posición actual de scroll + diferencia entre elemento y contenedor
    const scrollTop = contentArea.value.scrollTop
    const elementRelativeTop = elementRect.top - containerRect.top + scrollTop

    // Offset para dejar espacio visual arriba (16px de margen)
    const offset = 16

    contentArea.value.scrollTo({
      top: elementRelativeTop - offset,
      behavior: 'smooth'
    })
    activeSection.value = sectionId
  }
}

const handleScroll = () => {
  if (!contentArea.value) return

  const sections = ['apariencia', 'analisis', 'metodos-nlp', 'notificaciones', 'privacidad', 'correcciones', 'mantenimiento', 'acerca-de']
  const scrollPosition = contentArea.value.scrollTop + 100

  for (const sectionId of sections) {
    const element = document.getElementById(sectionId)
    if (element) {
      const offsetTop = element.offsetTop
      const offsetBottom = offsetTop + element.offsetHeight

      if (scrollPosition >= offsetTop && scrollPosition < offsetBottom) {
        activeSection.value = sectionId
        break
      }
    }
  }
}
</script>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-0);
  flex-shrink: 0;
}

/* Dark mode para header */
:global(.dark) .settings-header {
  background: var(--p-surface-900);
  border-bottom-color: var(--p-surface-700);
}

.settings-header h1 {
  margin: 0;
  font-size: 2rem;
}

.settings-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.settings-sidebar {
  width: 250px;
  flex-shrink: 0;
  background: var(--p-surface-0);
  border-right: 1px solid var(--p-surface-200);
  overflow-y: auto;
  padding: 1.5rem 0;
}

/* Dark mode para sidebar */
:global(.dark) .settings-sidebar {
  background: var(--p-surface-900);
  border-right-color: var(--p-surface-700);
}

.nav-menu {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-menu li {
  margin: 0;
}

.nav-menu a,
.nav-menu a:link,
.nav-menu a:visited,
.nav-menu a:hover,
.nav-menu a:active {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  color: var(--p-text-color);
  text-decoration: none !important;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  border-left: 3px solid transparent;
  cursor: pointer;
  user-select: none;
}

.nav-menu a:hover {
  background: var(--p-surface-100);
  color: var(--p-primary-color);
}

.nav-menu a.active {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  color: var(--p-primary-color);
  border-left-color: var(--p-primary-color);
  font-weight: 600;
}

/* Dark mode para navegación */
:global(.dark) .nav-menu a:hover {
  background: var(--p-surface-800);
}

:global(.dark) .nav-menu a.active {
  background: color-mix(in srgb, var(--p-primary-color) 20%, transparent);
}

.nav-menu a i {
  font-size: 1.1rem;
  width: 1.5rem;
  text-align: center;
  text-decoration: none !important;
}

.nav-menu a span {
  font-size: 0.95rem;
  text-decoration: none !important;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  scroll-behavior: smooth;
}

.settings-content > :deep(*) {
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.settings-content > :deep(.p-card) {
  margin-bottom: 1.5rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
}

.section-title i {
  color: var(--p-primary-color);
}

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

/* Layout de columna para items con contenido ancho */
.setting-item.column {
  flex-direction: column;
  gap: 1rem;
}

.setting-item.column .setting-info {
  padding-right: 0;
  max-width: 100%;
}

.setting-item.column .setting-control,
.setting-item.column .system-patterns-list,
.setting-item.column .correction-config-summary,
.setting-item.column .user-rejections-list {
  width: 100%;
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

.setting-description code {
  background: var(--p-surface-100);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.85rem;
}

:global(.dark) .setting-description code {
  background: var(--p-surface-800);
}

.setting-control {
  min-width: 200px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

/* Sliders necesitan ancho completo */
.setting-control :deep(.p-slider) {
  width: 100%;
}

.about-info {
  text-align: center;
}

.about-info h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-primary-color);
}

.about-info .version {
  margin: 0 0 1rem 0;
  color: var(--p-text-muted-color);
  font-weight: 500;
}

.about-info .description {
  margin: 0 0 1.5rem 0;
  color: var(--p-text-muted-color);
  line-height: 1.6;
}

.about-links {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

/* LLM / Inferencia section */
.setting-control.wide {
  min-width: 350px;
}

.method-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.75rem;
  gap: 1rem;
}

.method-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.method-name {
  font-weight: 500;
}

.method-desc {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.method-badges {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.speed-badge {
  font-size: 0.7rem;
}

/* MultiSelect styling - estilos específicos del componente */
/* Los estilos globales del panel están en primevue-overrides.css */
.setting-control.wide :deep(.p-multiselect) {
  width: 100%;
}

/* Badges de velocidad - alineación vertical */
.method-badges :deep(.p-tag) {
  padding: 0.2rem 0.5rem;
  line-height: 1;
}

/* Message styling */
.info-message {
  margin-top: 1rem;
}

.info-message :deep(.p-message-wrapper) {
  padding: 0.75rem 1rem;
  gap: 0.75rem;
}

.info-message .message-content {
  line-height: 1.5;
}

.info-message .message-content code {
  padding: 0.125rem 0.375rem;
  margin: 0 0.125rem;
  background: var(--p-surface-200);
  border-radius: 0.25rem;
  font-size: 0.85em;
}

:global(.dark) .info-message .message-content code {
  background: var(--p-surface-700);
}

.info-message .message-content a {
  color: var(--p-primary-color);
  text-decoration: underline;
}

/* ============================================================================
   Métodos de Análisis - Sección de configuración granular
   ============================================================================ */

.hardware-banner {
  margin-bottom: 1.5rem;
}

.hardware-banner :deep(.p-message-wrapper) {
  padding: 0.75rem 1rem;
}

.hardware-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.hardware-info i {
  font-size: 1.25rem;
}

.hardware-info div {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.hardware-info span {
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}

.nlp-category {
  margin-bottom: 2rem;
}

.nlp-category:last-of-type {
  margin-bottom: 1rem;
}

.category-header {
  margin-bottom: 1rem;
}

.category-header h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.category-header h4 i {
  color: var(--p-primary-color);
}

.category-desc {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.methods-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.method-card {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  padding: 1rem;
  transition: all 0.15s ease;
}

:global(.dark) .method-card {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

.method-card.enabled {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-surface-50));
}

:global(.dark) .method-card.enabled {
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-surface-800));
}

.method-card.disabled {
  opacity: 0.6;
}

.method-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.method-header .method-name {
  font-weight: 600;
  font-size: 0.95rem;
  flex: 1;
  min-width: 120px;
}

.method-tag {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  font-weight: 600;
}

/* Tags de método con mejor visibilidad en todos los modos */
.method-card .method-tag.p-tag-info {
  background: var(--blue-100) !important;
  color: var(--blue-700) !important;
  border: 1px solid var(--blue-300) !important;
}

.method-card .method-tag.p-tag-warning {
  background: var(--yellow-100) !important;
  color: var(--yellow-800) !important;
  border: 1px solid var(--yellow-400) !important;
}

.method-card .method-tag.p-tag-danger {
  background: var(--red-100) !important;
  color: var(--red-700) !important;
  border: 1px solid var(--red-300) !important;
}

/* Dark mode: Tags con fondo más visible */
:global(.dark) .method-card .method-tag.p-tag-info {
  background: var(--blue-900) !important;
  color: var(--blue-200) !important;
  border: 1px solid var(--blue-600) !important;
}

:global(.dark) .method-card .method-tag.p-tag-warning {
  background: var(--yellow-900) !important;
  color: var(--yellow-200) !important;
  border: 1px solid var(--yellow-600) !important;
}

:global(.dark) .method-card .method-tag.p-tag-danger {
  background: var(--red-900) !important;
  color: var(--red-200) !important;
  border: 1px solid var(--red-600) !important;
}

.method-description {
  margin: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}

.method-weight {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

/* Ollama ready bar - compacto cuando está listo */
.ollama-ready-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: var(--green-50);
  border: 1px solid var(--green-200);
  border-radius: 6px;
  margin-bottom: 1rem;
}

.ollama-ready-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--green-700);
}

.ollama-ready-info i {
  color: var(--green-500);
}

/* Ollama action card - cuando necesita acción */
.ollama-action-card {
  background: var(--yellow-50);
  border: 1px solid var(--yellow-200);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
}

.ollama-action-card.ollama-state-no_models {
  background: var(--blue-50);
  border-color: var(--blue-200);
}

.ollama-action-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.ollama-action-content > i {
  font-size: 1.25rem;
  color: var(--yellow-600);
  flex-shrink: 0;
}

.ollama-action-card.ollama-state-no_models .ollama-action-content > i {
  color: var(--blue-500);
}

.ollama-action-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.ollama-action-text strong {
  font-size: 0.9rem;
  color: var(--p-text-color);
}

.ollama-action-text span {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

/* Ollama download progress bar */
.ollama-progress-wrapper {
  width: 100%;
  margin-top: 0.5rem;
}

/* LanguageTool progress bar */
.lt-progress-container {
  margin-top: 0.5rem;
  width: 100%;
}

/* Setting deshabilitado visualmente */
.setting-item.setting-disabled {
  opacity: 0.6;
}

/* Dark mode para Ollama */
:global(.dark) .ollama-ready-bar {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--green-800);
}

:global(.dark) .ollama-ready-info {
  color: var(--green-400);
}

:global(.dark) .ollama-action-card {
  background: rgba(234, 179, 8, 0.1);
  border-color: var(--yellow-800);
}

:global(.dark) .ollama-action-card.ollama-state-no_models {
  background: rgba(59, 130, 246, 0.1);
  border-color: var(--blue-800);
}

:global(.dark) .ollama-action-content > i {
  color: var(--yellow-400);
}

:global(.dark) .ollama-action-card.ollama-state-no_models .ollama-action-content > i {
  color: var(--blue-400);
}

/* ============================================================================
   Data Location Dialog
   ============================================================================ */

.data-location-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.dialog-description {
  margin: 0;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.location-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-label {
  font-weight: 600;
  font-size: 0.9rem;
}

.location-field {
  width: 100%;
}

.migrate-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

:global(.dark) .migrate-option {
  background: var(--p-surface-800);
}

.migrate-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.migrate-info label {
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
}

.migrate-description {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.location-info-message {
  margin: 0;
}

.location-info-message :deep(.p-message-wrapper) {
  padding: 0.75rem 1rem;
}

/* ============================================================================
   Sistema de Sensibilidad Unificado
   ============================================================================ */

.sensitivity-section {
  padding: 0.5rem 0;
}

.sensitivity-header {
  margin-bottom: 1.25rem;
}

.sensitivity-header .setting-label {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

/* Presets como botones grandes */
.sensitivity-presets {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.preset-button {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: var(--p-surface-50);
  border: 2px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  width: 100%;
}

.preset-button:hover {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-surface-50));
}

.preset-button.active {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-surface-50));
}

.preset-button > i:first-child {
  font-size: 1.5rem;
  color: var(--p-text-muted-color);
  width: 2rem;
  text-align: center;
}

.preset-button.active > i:first-child {
  color: var(--p-primary-color);
}

.preset-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.preset-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--p-text-color);
}

.preset-button .preset-desc {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.recommended-star {
  color: var(--yellow-500);
  font-size: 0.9rem;
}

/* Dark mode para presets */
:global(.dark) .preset-button {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) .preset-button:hover {
  background: color-mix(in srgb, var(--p-primary-color) 15%, var(--p-surface-800));
}

:global(.dark) .preset-button.active {
  background: color-mix(in srgb, var(--p-primary-color) 20%, var(--p-surface-800));
}

/* Slider de ajuste fino */
.sensitivity-slider {
  padding: 1rem 1.25rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
  margin-bottom: 1rem;
}

:global(.dark) .sensitivity-slider {
  background: var(--p-surface-800);
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.slider-label {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--p-text-color);
}

.slider-value {
  font-size: 0.85rem;
  color: var(--p-primary-color);
  font-weight: 600;
}

.slider-hints {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

/* Panel avanzado */
.advanced-panel {
  border-top: 1px solid var(--p-surface-200);
  padding-top: 1rem;
  margin-top: 0.5rem;
}

:global(.dark) .advanced-panel {
  border-top-color: var(--p-surface-700);
}

.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0.5rem 0;
  transition: color 0.15s ease;
}

.advanced-toggle:hover {
  color: var(--p-primary-color);
}

.advanced-toggle i {
  font-size: 0.75rem;
}

.advanced-content {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

:global(.dark) .advanced-content {
  background: var(--p-surface-800);
}

.advanced-note {
  margin: 0 0 1rem 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.advanced-slider {
  margin-bottom: 1rem;
}

.advanced-slider:last-of-type {
  margin-bottom: 1.25rem;
}

.advanced-slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.advanced-slider-header label {
  font-size: 0.85rem;
  color: var(--p-text-color);
}

.advanced-slider-header span {
  font-size: 0.85rem;
  color: var(--p-primary-color);
  font-weight: 500;
}

.slider-help {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
  margin: 0 0 0.5rem 0;
  line-height: 1.4;
}

/* ============================================================================
   Filtros de Entidades
   ============================================================================ */

.section-description {
  color: var(--p-text-secondary-color);
  font-size: 0.9rem;
  line-height: 1.5;
}

.filter-stats {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
}

:global(.dark) .filter-stats {
  background: var(--p-surface-800);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-primary-color);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
}

.system-patterns-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.pattern-category {
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  overflow: hidden;
}

:global(.dark) .pattern-category {
  border-color: var(--p-surface-700);
}

.category-title {
  margin: 0;
  padding: 0.75rem 1rem;
  background: var(--p-surface-100);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--p-text-color);
}

:global(.dark) .category-title {
  background: var(--p-surface-800);
}

.patterns-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.5rem;
  padding: 0.75rem;
}

.pattern-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: var(--p-border-radius);
  transition: background 0.15s ease;
}

.pattern-item:hover {
  background: var(--p-surface-100);
}

:global(.dark) .pattern-item:hover {
  background: var(--p-surface-800);
}

.pattern-item.inactive {
  opacity: 0.5;
}

.pattern-label {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  cursor: pointer;
}

.pattern-text {
  font-family: var(--p-font-family-mono, monospace);
  font-size: 0.8rem;
  color: var(--p-text-color);
  background: var(--p-surface-200);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
}

:global(.dark) .pattern-text {
  background: var(--p-surface-700);
}

.pattern-desc {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
}

.loading-patterns {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  color: var(--p-text-secondary-color);
}

.user-rejections-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 300px;
  overflow-y: auto;
}

.rejection-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
}

:global(.dark) .rejection-item {
  background: var(--p-surface-800);
}

.rejection-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.rejection-name {
  font-weight: 500;
  color: var(--p-text-color);
}

.rejection-reason {
  font-size: 0.85rem;
  color: var(--p-text-secondary-color);
}

.empty-rejections {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  color: var(--p-text-secondary-color);
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
}

:global(.dark) .empty-rejections {
  background: var(--p-surface-800);
}

.empty-rejections i {
  font-size: 1.25rem;
  color: var(--p-green-500);
}

/* ============================================================================
   Configuracion de Correcciones
   ============================================================================ */

.correction-info-message {
  font-size: 0.9rem;
  line-height: 1.5;
}

.correction-info-message p {
  margin: 0;
}

.correction-config-summary {
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
  padding: 1rem;
}

:global(.dark) .correction-config-summary {
  background: var(--p-surface-800);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.config-section {
  background: var(--p-surface-0);
  border-radius: var(--p-border-radius);
  padding: 1rem;
}

:global(.dark) .config-section {
  background: var(--p-surface-900);
}

.config-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--p-primary-color);
}

.config-section h4 i {
  font-size: 1rem;
}

.config-items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.config-label {
  color: var(--p-text-secondary-color);
  min-width: 80px;
}

.preset-dropdown-option {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.preset-dropdown-option .preset-name {
  font-weight: 500;
}

.preset-dropdown-option .preset-description {
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
}

.text-green-500 {
  color: var(--p-green-500);
}

.text-red-500 {
  color: var(--p-red-500);
}

/* Character Knowledge Mode Selector */
.knowledge-mode-selector {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.knowledge-mode-card {
  flex: 1;
  min-width: 200px;
  padding: 1rem;
  border: 2px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius);
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--p-surface-ground);
}

.knowledge-mode-card:hover:not(.disabled) {
  border-color: var(--p-primary-color);
  background: var(--p-surface-hover);
}

.knowledge-mode-card.selected {
  border-color: var(--p-primary-color);
  background: var(--p-primary-50);
}

.knowledge-mode-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.knowledge-mode-card .mode-name {
  font-weight: 600;
  font-size: 1rem;
}

.knowledge-mode-card .mode-description {
  font-size: 0.85rem;
  color: var(--p-text-secondary-color);
  line-height: 1.4;
}


.knowledge-mode-card .method-tag {
  margin-top: 0.5rem;
  width: fit-content;
}
</style>
