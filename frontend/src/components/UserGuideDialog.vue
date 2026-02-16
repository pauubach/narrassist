<template>
  <Dialog
    :visible="visible"
    modal
    :style="{ width: '800px', maxHeight: '85vh' }"
    :dismissable-mask="true"
    :draggable="false"
    class="user-guide-dialog"
    @update:visible="$emit('update:visible', $event)"
  >
    <template #header>
      <div class="guide-header">
        <i class="pi pi-book"></i>
        <span>Guía de Usuario</span>
      </div>
    </template>

    <div class="guide-content">
      <!-- Navegación lateral -->
      <nav class="guide-nav">
        <ul>
          <li
            v-for="section in sections"
            :key="section.id"
            :class="{ active: activeSection === section.id }"
            @click="scrollToSection(section.id)"
          >
            <i :class="section.icon"></i>
            <span>{{ section.title }}</span>
          </li>
        </ul>
      </nav>

      <!-- Contenido -->
      <div ref="guideBody" class="guide-body">
        <!-- Introducción -->
        <section id="introduccion" class="guide-section">
          <h2><i class="pi pi-home"></i> ¿Qué es Narrative Assistant?</h2>
          <p>
            <strong>Narrative Assistant</strong> es una herramienta de asistencia para
            <strong>escritores, editores y correctores profesionales</strong>. Te ayuda a detectar
            inconsistencias y errores en cualquier tipo de manuscrito de forma automática.
          </p>

          <div class="genre-examples">
            <span class="genre-tag">Novelas</span>
            <span class="genre-tag">Memorias</span>
            <span class="genre-tag">Autoayuda</span>
            <span class="genre-tag">Libros de cocina</span>
            <span class="genre-tag">Ensayos</span>
            <span class="genre-tag">Manuales técnicos</span>
            <span class="genre-tag">Y más...</span>
          </div>

          <div class="feature-list">
            <div class="feature-item">
              <i class="pi pi-tags"></i>
              <div>
                <strong>Entidades</strong>
                <p>Detecta personas, lugares, conceptos y términos clave del documento</p>
              </div>
            </div>
            <div class="feature-item">
              <i class="pi pi-search"></i>
              <div>
                <strong>Coherencia</strong>
                <p>Verifica que nombres, términos y datos se usen de forma consistente</p>
              </div>
            </div>
            <div class="feature-item">
              <i class="pi pi-exclamation-triangle"></i>
              <div>
                <strong>Inconsistencias</strong>
                <p>Alerta sobre errores de continuidad, ortografía y gramática</p>
              </div>
            </div>
            <div class="feature-item">
              <i class="pi pi-shield"></i>
              <div>
                <strong>100% Privado</strong>
                <p>Tu manuscrito nunca sale de tu ordenador</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Primeros pasos -->
        <section id="primeros-pasos" class="guide-section">
          <h2><i class="pi pi-play"></i> Primeros Pasos</h2>

          <h3>1. Crear un proyecto</h3>
          <p>
            Haz clic en <strong>"Nuevo Proyecto"</strong> en la pantalla de inicio.
            Cada proyecto corresponde a un manuscrito o libro.
          </p>

          <h3>2. Importar tu documento</h3>
          <p>Arrastra tu archivo o haz clic para seleccionarlo. Formatos soportados:</p>
          <ul>
            <li><strong>.docx</strong> - Microsoft Word (recomendado)</li>
            <li><strong>.doc</strong> - Word clásico</li>
            <li><strong>.txt</strong> - Texto plano</li>
            <li><strong>.md</strong> - Markdown</li>
            <li><strong>.pdf</strong> - PDF</li>
            <li><strong>.epub</strong> - Libro electrónico</li>
          </ul>

          <h3>3. Analizar</h3>
          <p>
            Una vez importado, el análisis comienza automáticamente. Verás una barra
            de progreso con las diferentes fases:
          </p>
          <ul>
            <li>Extracción de texto y secciones</li>
            <li>Identificación de entidades (personas, lugares, conceptos)</li>
            <li>Análisis de relaciones y apariciones</li>
            <li>Detección de posibles inconsistencias</li>
          </ul>
        </section>

        <!-- Interfaz principal -->
        <section id="interfaz" class="guide-section">
          <h2><i class="pi pi-desktop"></i> La Interfaz</h2>

          <h3>Barra lateral izquierda</h3>
          <p>Navegación rápida con cuatro pestañas:</p>
          <ul>
            <li><strong>Capítulos</strong> - Secciones del documento, clic para navegar</li>
            <li><strong>Alertas</strong> - Lista de inconsistencias detectadas</li>
            <li><strong>Personajes</strong> - Entidades detectadas con sus apariciones</li>
            <li><strong>Asistente</strong> - Ayuda contextual</li>
          </ul>

          <h3>Área central: Workspace</h3>
          <p>
            Pestañas superiores para acceder a las distintas vistas de análisis.
            Según el tipo de documento se muestran las pestañas relevantes:
          </p>
          <ul>
            <li><strong>Texto</strong> - Vista del manuscrito con resaltado de entidades e inconsistencias</li>
            <li><strong>Entidades</strong> - Gestión completa de personajes, lugares y conceptos</li>
            <li><strong>Relaciones</strong> - Red de relaciones entre entidades</li>
            <li><strong>Revisión</strong> - Panel de alertas con modo foco</li>
            <li><strong>Cronología</strong> - Línea temporal de eventos</li>
            <li><strong>Escritura</strong> - Análisis de voz, estilo y prosa</li>
            <li><strong>Glosario</strong> - Términos y definiciones del manuscrito</li>
            <li><strong>Resumen</strong> - Vista general del proyecto y métricas</li>
          </ul>

          <h3>Resaltado del texto</h3>
          <div class="color-legend">
            <div class="legend-item">
              <span class="color-dot person"></span>
              <span>Entidades</span>
            </div>
            <div class="legend-item">
              <span class="color-dot location"></span>
              <span>Lugares</span>
            </div>
            <div class="legend-item">
              <span class="color-dot alert"></span>
              <span>Posibles inconsistencias</span>
            </div>
          </div>
        </section>

        <!-- Alertas -->
        <section id="alertas" class="guide-section">
          <h2><i class="pi pi-bell"></i> Alertas e Inconsistencias</h2>

          <p>
            El sistema detecta automáticamente posibles problemas. No todas las
            alertas son errores reales - algunas pueden ser decisiones narrativas
            intencionales.
          </p>

          <h3>Tipos de alertas</h3>
          <div class="alert-types">
            <div class="alert-type">
              <Tag severity="danger" value="Alta" />
              <p>Inconsistencias graves que probablemente son errores</p>
            </div>
            <div class="alert-type">
              <Tag severity="warning" value="Media" />
              <p>Posibles problemas que conviene revisar</p>
            </div>
            <div class="alert-type">
              <Tag severity="info" value="Baja" />
              <p>Sugerencias o patrones inusuales</p>
            </div>
          </div>

          <h3>Gestionar alertas</h3>
          <ul>
            <li><strong>Revisar</strong> - Haz clic en una alerta para ver el contexto</li>
            <li><strong>Resolver</strong> - Marca como resuelta si ya la corregiste</li>
            <li><strong>Descartar</strong> - Si es intencional, descártala</li>
            <li><strong>Notas</strong> - Añade comentarios para recordar decisiones</li>
          </ul>
        </section>

        <!-- Entidades -->
        <section id="personajes" class="guide-section">
          <h2><i class="pi pi-tags"></i> Gestión de Entidades</h2>

          <p>
            El sistema identifica automáticamente entidades relevantes: personas,
            organizaciones, conceptos, ingredientes, técnicas y otros términos clave
            según el tipo de documento.
          </p>

          <h3>Ficha de entidad</h3>
          <p>Para cada entidad verás:</p>
          <ul>
            <li><strong>Nombre principal</strong> y variantes detectadas</li>
            <li><strong>Primera aparición</strong> en el texto</li>
            <li><strong>Número de apariciones</strong> totales</li>
            <li><strong>Secciones</strong> en las que aparece</li>
            <li><strong>Relaciones</strong> con otras entidades</li>
          </ul>

          <h3>Correcciones manuales</h3>
          <p>
            Si el sistema confunde dos entidades o no detecta que dos términos
            se refieren a lo mismo, puedes:
          </p>
          <ul>
            <li><strong>Fusionar</strong> - Unir dos entidades en una</li>
            <li><strong>Dividir</strong> - Separar apariciones incorrectamente agrupadas</li>
            <li><strong>Renombrar</strong> - Cambiar el nombre principal</li>
          </ul>
        </section>

        <!-- Áreas de trabajo -->
        <section id="workspace" class="guide-section">
          <h2><i class="pi pi-th-large"></i> Áreas de Trabajo</h2>

          <h3>Relaciones</h3>
          <p>
            Visualiza las conexiones entre personajes y entidades en un grafo interactivo.
            Puedes ver quién interactúa con quién, la frecuencia de interacciones
            y los tipos de relación (familiar, profesional, etc.).
          </p>

          <h3>Revisión (Alertas)</h3>
          <p>
            Panel avanzado para revisar inconsistencias. Incluye un <strong>modo foco</strong>
            que te guía secuencialmente por cada alerta, mostrando el contexto del texto
            y permitiéndote resolver, descartar o añadir notas a cada una.
          </p>

          <h3>Cronología</h3>
          <p>
            Muestra los eventos detectados en el manuscrito ordenados en el tiempo.
            Útil para detectar inconsistencias temporales (ej: un evento que ocurre
            antes de otro que debería ser previo).
          </p>

          <h3>Escritura</h3>
          <p>
            Analiza el estilo y la voz del manuscrito. Incluye:
          </p>
          <ul>
            <li><strong>Perfiles de voz</strong> - Registro, formalidad y tono por personaje</li>
            <li><strong>Métricas de prosa</strong> - Legibilidad, longitud de oraciones, ritmo</li>
            <li><strong>Consistencia de registro</strong> - Detecta cambios bruscos de estilo</li>
          </ul>

          <h3>Glosario</h3>
          <p>
            Recopilación automática de términos relevantes del manuscrito con sus
            definiciones contextuales y frecuencia de uso.
          </p>

          <h3>Entidades enriquecidas</h3>
          <p>
            La pestaña de Entidades incluye relaciones entre personajes,
            estado vital y datos enriquecidos del universo narrativo.
          </p>
        </section>

        <!-- Asistente IA -->
        <section id="asistente-ia" class="guide-section">
          <h2><i class="pi pi-comments"></i> Asistente IA</h2>

          <p>
            El <strong>Asistente IA</strong> es un chat inteligente que conoce tu manuscrito
            completo. Puedes hacerle preguntas y obtener respuestas con
            <strong>referencias navegables</strong> al texto original.
          </p>

          <h3>Preguntas sobre el manuscrito</h3>
          <p>
            Escribe tu pregunta en el panel del asistente (sidebar izquierdo,
            pestaña <i class="pi pi-comments"></i>). El asistente buscará
            en <strong>todos los capítulos</strong> para encontrar la información relevante.
          </p>

          <div class="tip-box">
            <i class="pi pi-lightbulb"></i>
            <div>
              <strong>Ejemplo:</strong> "¿De qué color son los ojos de María?"
              — El asistente buscará todas las menciones en el manuscrito y
              te indicará si hay inconsistencias entre capítulos.
            </div>
          </div>

          <h3>Texto seleccionado como contexto</h3>
          <p>
            Selecciona texto en el visor de documento y haz clic en
            <strong>"Preguntar a la IA"</strong> en el panel de selección.
            El asistente usará ese fragmento como contexto para responder tu pregunta
            con mayor precisión.
          </p>
          <p>
            Cuando hay texto seleccionado, verás una barra azul sobre el campo
            de entrada mostrando el fragmento. Puedes cerrarla con la ✕ si
            prefieres preguntar sin contexto.
          </p>

          <h3>Referencias navegables</h3>
          <p>
            Las respuestas del asistente incluyen <strong>referencias clicables</strong>
            al texto original. Haz clic en una referencia para navegar directamente
            a esa parte del manuscrito, igual que con las alertas.
          </p>
          <p>
            Si el asistente encuentra información contradictoria (por ejemplo,
            "ojos azules" en un capítulo y "ojos verdes" en otro), citará
            ambas ubicaciones para que puedas verificarlo tú mismo.
          </p>

          <h3>Preguntas sugeridas</h3>
          <ul>
            <li>"¿Cuántas veces aparece [personaje]?"</li>
            <li>"¿Qué se dice sobre [lugar/objeto] en el manuscrito?"</li>
            <li>"¿Hay inconsistencias con [atributo] de [personaje]?"</li>
            <li>"Resúmeme lo que pasa en este fragmento" (con texto seleccionado)</li>
            <li>"¿Quién habla en este diálogo?" (con texto seleccionado)</li>
          </ul>
        </section>

        <!-- Exportar -->
        <section id="exportar" class="guide-section">
          <h2><i class="pi pi-download"></i> Exportar</h2>

          <p>
            Desde el menú <strong>Archivo → Exportar</strong> o el botón de exportar
            en la vista de proyecto, puedes generar:
          </p>

          <h3>Documento completo</h3>
          <p>
            Informe profesional en <strong>Word (.docx)</strong> o <strong>PDF</strong> con portada,
            índice y todas las secciones del análisis.
          </p>

          <h3>Informe de análisis</h3>
          <p>
            Resumen de alertas, entidades y métricas en <strong>Markdown</strong> o <strong>JSON</strong>.
            Ideal para integrar con otras herramientas.
          </p>

          <h3>Guía de estilo</h3>
          <p>
            Documento con las convenciones de escritura, voces narrativas y
            perfiles de personajes en <strong>Markdown</strong>, <strong>JSON</strong> o <strong>PDF</strong>.
          </p>

          <h3>Exportar a Scrivener</h3>
          <p>
            Genera un paquete <strong>.scriv</strong> compatible con Scrivener 3, conservando
            capítulos, escenas y metadatos del análisis.
          </p>
        </section>

        <!-- Configuración -->
        <section id="configuracion" class="guide-section">
          <h2><i class="pi pi-cog"></i> Configuración</h2>

          <h3>Apariencia</h3>
          <ul>
            <li><strong>Tema</strong> - Claro, oscuro o automático según tu sistema</li>
            <li><strong>Densidad</strong> - Ajusta el espaciado de la interfaz</li>
            <li><strong>Tipografía</strong> - Cambia la fuente de lectura</li>
          </ul>

          <h3>Análisis</h3>
          <ul>
            <li><strong>Analizador semántico</strong> - Motor de IA local para análisis avanzado de personajes y relaciones</li>
            <li><strong>LanguageTool</strong> - Corrector gramatical avanzado con +2000 reglas para español</li>
            <li><strong>Sensibilidad</strong> - Ajusta qué tan estricta es la detección de problemas</li>
          </ul>

          <p class="analysis-note">
            Ambos componentes son opcionales y se ejecutan 100% en local.
            Se instalan automáticamente la primera vez desde la pantalla de bienvenida.
          </p>

          <h3>Notificaciones</h3>
          <ul>
            <li><strong>Notificaciones</strong> - Aviso cuando el análisis termine</li>
            <li><strong>Sonidos</strong> - Feedback auditivo para eventos</li>
          </ul>
        </section>

        <!-- Privacidad -->
        <section id="privacidad" class="guide-section">
          <h2><i class="pi pi-shield"></i> Privacidad y Seguridad</h2>

          <div class="privacy-highlight">
            <i class="pi pi-lock"></i>
            <div>
              <strong>Tu manuscrito NUNCA sale de tu ordenador</strong>
              <p>
                Narrative Assistant usa inteligencia artificial local para analizar tu texto.
                Todo el procesamiento ocurre en tu máquina - tu manuscrito jamás se sube a internet.
              </p>
            </div>
          </div>

          <div class="ai-info-box">
            <h4><i class="pi pi-microchip-ai"></i> Análisis asistido por IA</h4>
            <p>
              El sistema utiliza modelos de inteligencia artificial que se ejecutan
              <strong>100% en local</strong> en tu ordenador:
            </p>
            <ul>
              <li><strong>Modelos NLP</strong> - Para detectar entidades y analizar texto</li>
              <li><strong>IA local</strong> - Para análisis semántico avanzado</li>
            </ul>
            <p class="ai-privacy-note">
              <i class="pi pi-download"></i> Se pueden <strong>descargar</strong> modelos y actualizaciones.
              <br />
              <i class="pi pi-ban"></i> <strong>Nunca se sube</strong> ningún contenido de tu manuscrito.
            </p>
          </div>

          <h3>¿Dónde se guardan mis datos?</h3>
          <p>
            Los proyectos se almacenan localmente en tu ordenador. Puedes ver
            y cambiar la ubicación en Ajustes → Privacidad y Datos.
          </p>

          <h3>¿Qué conexión necesita la app?</h3>
          <ul>
            <li><strong>Verificación de licencia</strong> - Única comunicación con servidores</li>
            <li><strong>Descarga de modelos</strong> - Solo la primera vez o para actualizaciones</li>
            <li><strong>Análisis de texto</strong> - 100% offline, sin conexión necesaria</li>
          </ul>
        </section>

        <!-- Atajos -->
        <section id="atajos" class="guide-section">
          <h2><i class="pi pi-bolt"></i> Atajos de Teclado</h2>

          <div class="shortcuts-grid">
            <div class="shortcut">
              <kbd>Ctrl</kbd> + <kbd>N</kbd>
              <span>Nuevo proyecto</span>
            </div>
            <div class="shortcut">
              <kbd>Ctrl</kbd> + <kbd>O</kbd>
              <span>Abrir proyecto</span>
            </div>
            <div class="shortcut">
              <kbd>Ctrl</kbd> + <kbd>S</kbd>
              <span>Guardar</span>
            </div>
            <div class="shortcut">
              <kbd>Ctrl</kbd> + <kbd>F</kbd>
              <span>Buscar en documento</span>
            </div>
            <div class="shortcut">
              <kbd>Ctrl</kbd> + <kbd>,</kbd>
              <span>Abrir ajustes</span>
            </div>
            <div class="shortcut">
              <kbd>Ctrl</kbd> + <kbd>D</kbd>
              <span>Cambiar tema claro/oscuro</span>
            </div>
            <div class="shortcut">
              <kbd>F1</kbd>
              <span>Esta ayuda</span>
            </div>
            <div class="shortcut">
              <kbd>Esc</kbd>
              <span>Cerrar diálogo</span>
            </div>
          </div>
        </section>

        <!-- FAQ -->
        <section id="faq" class="guide-section">
          <h2><i class="pi pi-question-circle"></i> Preguntas Frecuentes</h2>

          <div class="faq-item">
            <h4>¿Por qué el análisis tarda tanto?</h4>
            <p>
              El tiempo depende del tamaño del manuscrito y de tu hardware.
              Un documento de 100.000 palabras puede tardar varios minutos.
              Si tienes GPU, el análisis será más rápido.
            </p>
          </div>

          <div class="faq-item">
            <h4>¿Puedo analizar varios libros a la vez?</h4>
            <p>
              Sí, cada libro es un proyecto independiente. Puedes tener
              varios proyectos abiertos, pero el análisis se ejecuta de uno en uno.
            </p>
          </div>

          <div class="faq-item">
            <h4>El sistema no detecta una entidad correctamente</h4>
            <p>
              Puedes corregirlo manualmente. Haz clic derecho sobre la palabra
              y selecciona "Asignar a entidad" para indicar a qué se refiere.
            </p>
          </div>

          <div class="faq-item">
            <h4>¿Qué significa "Analizador semántico no disponible"?</h4>
            <p>
              El análisis avanzado requiere un componente adicional (se instala automáticamente).
              Ve a Ajustes → Métodos de Análisis y haz clic en
              "Configurar analizador" para instalarlo.
            </p>
          </div>

          <div class="faq-item">
            <h4>¿Cómo exporto el informe de inconsistencias?</h4>
            <p>
              En el menú Archivo → Exportar o con el botón Exportar en la vista de proyecto.
              Puedes elegir entre Word, PDF, Markdown, JSON o Scrivener según el tipo de informe.
            </p>
          </div>

          <div class="faq-item">
            <h4>¿Puedo re-analizar un documento ya analizado?</h4>
            <p>
              Sí, haz clic en "Re-analizar" en la vista de proyecto. Puedes seleccionar
              qué fases del análisis ejecutar de nuevo.
            </p>
          </div>

          <div class="faq-item">
            <h4>¿Qué es LanguageTool?</h4>
            <p>
              Es un corrector gramatical avanzado con más de 2000 reglas para español.
              Se instala automáticamente (~300 MB) y funciona 100% en local.
              Detecta errores ortográficos, gramaticales y de concordancia.
            </p>
          </div>
        </section>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onBeforeUnmount } from 'vue'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'

const props = defineProps<{
  visible: boolean
}>()

defineEmits<{
  'update:visible': [value: boolean]
}>()

const guideBody = ref<HTMLElement | null>(null)
const activeSection = ref('introduccion')
let scrollListenerAttached = false
let isManualScroll = false

const sections = [
  { id: 'introduccion', title: 'Introducción', icon: 'pi pi-home' },
  { id: 'primeros-pasos', title: 'Primeros Pasos', icon: 'pi pi-play' },
  { id: 'interfaz', title: 'La Interfaz', icon: 'pi pi-desktop' },
  { id: 'alertas', title: 'Alertas', icon: 'pi pi-bell' },
  { id: 'personajes', title: 'Entidades', icon: 'pi pi-tags' },
  { id: 'workspace', title: 'Áreas de Trabajo', icon: 'pi pi-th-large' },
  { id: 'asistente-ia', title: 'Asistente IA', icon: 'pi pi-comments' },
  { id: 'exportar', title: 'Exportar', icon: 'pi pi-download' },
  { id: 'configuracion', title: 'Configuración', icon: 'pi pi-cog' },
  { id: 'privacidad', title: 'Privacidad', icon: 'pi pi-shield' },
  { id: 'atajos', title: 'Atajos', icon: 'pi pi-bolt' },
  { id: 'faq', title: 'FAQ', icon: 'pi pi-question-circle' },
]

function scrollToSection(sectionId: string) {
  isManualScroll = true
  activeSection.value = sectionId
  const element = document.getElementById(sectionId)
  if (element && guideBody.value) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    // Allow scroll events to update again after smooth scroll finishes
    setTimeout(() => { isManualScroll = false }, 600)
  }
}

function updateActiveSection() {
  if (!guideBody.value || isManualScroll) return

  const container = guideBody.value
  const containerRect = container.getBoundingClientRect()
  // Threshold: 30% from top of the scrollable area
  const threshold = containerRect.top + containerRect.height * 0.3

  // Walk sections in reverse to find the last one whose top is above the threshold
  let found = false
  for (let i = sections.length - 1; i >= 0; i--) {
    const el = document.getElementById(sections[i].id)
    if (el) {
      const rect = el.getBoundingClientRect()
      if (rect.top <= threshold) {
        activeSection.value = sections[i].id
        found = true
        break
      }
    }
  }
  // If no section found above threshold, use the first one
  if (!found) {
    activeSection.value = sections[0].id
  }
}

function attachScrollListener() {
  if (guideBody.value && !scrollListenerAttached) {
    guideBody.value.addEventListener('scroll', updateActiveSection, { passive: true })
    scrollListenerAttached = true
  }
}

function detachScrollListener() {
  if (guideBody.value && scrollListenerAttached) {
    guideBody.value.removeEventListener('scroll', updateActiveSection)
    scrollListenerAttached = false
  }
}

// Attach/detach when dialog visibility changes
watch(() => props.visible, (isVisible) => {
  if (isVisible) {
    activeSection.value = 'introduccion'
    nextTick(() => {
      if (guideBody.value) {
        guideBody.value.scrollTop = 0
      }
      attachScrollListener()
    })
  } else {
    detachScrollListener()
  }
})

onBeforeUnmount(() => {
  detachScrollListener()
})
</script>

<style scoped>
.guide-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
}

.guide-header i {
  font-size: 1.5rem;
  color: var(--p-primary-color);
}

.guide-content {
  display: flex;
  gap: 1.5rem;
  height: 60vh;
  min-height: 400px;
}

.guide-nav {
  flex-shrink: 0;
  width: 180px;
  border-right: 1px solid var(--p-surface-border);
  padding-right: 1rem;
}

.guide-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.guide-nav li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  transition: all 0.2s ease;
}

.guide-nav li:hover {
  background: var(--p-surface-hover);
  color: var(--p-text-color);
}

.guide-nav li.active {
  background: var(--p-primary-color);
  color: white;
}

.guide-nav li i {
  font-size: 0.875rem;
  width: 1.25rem;
}

.guide-body {
  flex: 1;
  overflow-y: auto;
  padding-right: 1rem;
}

.guide-section {
  margin-bottom: 2.5rem;
  scroll-margin-top: 1rem;
}

.guide-section h2 {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--p-primary-color);
}

.guide-section h2 i {
  color: var(--p-primary-color);
}

.guide-section h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
  color: var(--p-text-color);
}

.guide-section h4 {
  font-size: 0.9375rem;
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.25rem;
}

.guide-section p {
  line-height: 1.6;
  color: var(--p-text-secondary-color);
  margin-bottom: 0.75rem;
}

.guide-section ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.guide-section li {
  line-height: 1.6;
  color: var(--p-text-secondary-color);
  margin-bottom: 0.25rem;
}

/* Genre examples */
.genre-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1rem 0;
}

.genre-tag {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  background: var(--p-surface-100);
  border: 1px solid var(--p-surface-border);
  border-radius: 20px;
  font-size: 0.8125rem;
  color: var(--p-text-secondary-color);
}

:global(.dark) .genre-tag {
  background: var(--p-surface-700);
}

/* Feature list */
.feature-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-top: 1rem;
}

.feature-item {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--p-surface-ground);
  border-radius: 8px;
  border: 1px solid var(--p-surface-border);
}

.feature-item i {
  font-size: 1.5rem;
  color: var(--p-primary-color);
  flex-shrink: 0;
}

.feature-item strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--p-text-color);
}

.feature-item p {
  font-size: 0.875rem;
  margin: 0;
}

/* Color legend */
.color-legend {
  display: flex;
  gap: 1.5rem;
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  background: var(--p-surface-ground);
  border-radius: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.color-dot.person {
  background: var(--blue-500);
}

.color-dot.location {
  background: var(--green-500);
}

.color-dot.alert {
  background: var(--orange-500);
}

/* Alert types */
.alert-types {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1rem 0;
}

.alert-type {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--p-surface-ground);
  border-radius: 6px;
}

.alert-type p {
  margin: 0;
  font-size: 0.875rem;
}

.analysis-note {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: var(--p-surface-ground);
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--p-text-secondary-color);
  border-left: 3px solid var(--p-primary-color);
}

/* Privacy highlight */
.privacy-highlight {
  display: flex;
  gap: 1rem;
  padding: 1.25rem;
  background: var(--green-50);
  border: 1px solid var(--green-200);
  border-radius: 8px;
  margin: 1rem 0;
}

:global(.dark) .privacy-highlight {
  background: var(--green-900);
  border-color: var(--green-700);
}

.privacy-highlight i {
  font-size: 2rem;
  color: var(--green-500);
}

.privacy-highlight strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--green-700);
}

:global(.dark) .privacy-highlight strong {
  color: var(--green-300);
}

.privacy-highlight p {
  margin: 0;
  font-size: 0.9375rem;
}

/* AI info box */
.ai-info-box {
  margin: 1.25rem 0;
  padding: 1rem 1.25rem;
  background: var(--p-surface-ground);
  border: 1px solid var(--p-surface-border);
  border-radius: 8px;
}

.ai-info-box h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  color: var(--p-primary-color);
}

.ai-info-box p {
  margin: 0.5rem 0;
}

.ai-info-box ul {
  margin: 0.5rem 0;
  padding-left: 1.25rem;
}

.ai-privacy-note {
  margin-top: 1rem !important;
  padding: 0.75rem;
  background: var(--blue-50);
  border-radius: 6px;
  font-size: 0.875rem;
  line-height: 1.8;
}

.ai-privacy-note i {
  margin-right: 0.25rem;
}

.ai-privacy-note .pi-download {
  color: var(--green-600);
}

.ai-privacy-note .pi-ban {
  color: var(--red-600);
}

:global(.dark) .ai-privacy-note {
  background: var(--blue-900);
}

/* Shortcuts grid */
.shortcuts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin: 1rem 0;
}

.shortcut {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--p-surface-ground);
  border-radius: 6px;
  font-size: 0.875rem;
}

.shortcut kbd {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  background: var(--p-surface-100);
  border: 1px solid var(--p-surface-border);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.8125rem;
}

.shortcut span {
  color: var(--p-text-secondary-color);
}

/* FAQ */
.faq-item {
  margin-bottom: 1.25rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--p-surface-border);
}

.faq-item:last-child {
  border-bottom: none;
}

.faq-item h4 {
  color: var(--p-text-color);
}

.faq-item p {
  margin: 0;
}
</style>
