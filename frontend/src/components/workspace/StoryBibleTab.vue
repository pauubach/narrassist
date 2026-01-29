<template>
  <div class="story-bible-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-book"></i>
          Story Bible
        </h3>
        <p class="subtitle">Wiki consolidada de todas las entidades del manuscrito.</p>
      </div>
      <div class="header-controls">
        <div class="type-filter">
          <Button
            v-for="t in entityTypes"
            :key="t.value"
            :label="t.label"
            :icon="t.icon"
            :outlined="filterType !== t.value"
            :badge="String(typeCounts[t.value] || 0)"
            badge-severity="secondary"
            size="small"
            @click="filterType = filterType === t.value ? null : t.value"
          />
        </div>
        <InputText v-model="searchQuery" placeholder="Buscar..." class="search-input" />
        <Button
          label="Cargar"
          icon="pi pi-refresh"
          :loading="loading"
          @click="loadBible"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando Story Bible...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="!bible" class="empty-state">
      <i class="pi pi-book"></i>
      <p>Haz clic en "Cargar" para construir la Story Bible del proyecto.</p>
    </div>

    <!-- Content: Sidebar + Detail -->
    <div v-else class="bible-layout">
      <!-- Sidebar -->
      <div class="bible-sidebar">
        <div v-if="!filteredEntries.length" class="sidebar-empty">
          Sin resultados.
        </div>
        <div
          v-for="entry in filteredEntries"
          :key="entry.entity_id"
          class="entity-item"
          :class="{ active: selectedId === entry.entity_id }"
          @click="selectedId = entry.entity_id"
        >
          <i :class="typeIcon(entry.entity_type)" class="entity-icon" />
          <div class="entity-info">
            <span class="entity-name">{{ entry.canonical_name }}</span>
            <span class="entity-meta">
              <Tag
                v-if="entry.importance"
                :value="importanceLabel(entry.importance)"
                :severity="importanceSeverity(entry.importance)"
                class="importance-tag"
              />
              <span class="mention-count">{{ entry.mention_count }} menciones</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Detail panel -->
      <div class="bible-detail">
        <div v-if="!selected" class="detail-empty">
          <i class="pi pi-arrow-left"></i>
          <p>Selecciona una entidad de la lista.</p>
        </div>
        <template v-else>
          <!-- Detail header -->
          <div class="detail-header">
            <i :class="typeIcon(selected.entity_type)" class="detail-type-icon" />
            <div>
              <h2 class="detail-name">{{ selected.canonical_name }}</h2>
              <div class="detail-subtitle">
                <Tag :value="typeLabel(selected.entity_type)" severity="info" />
                <Tag
                  v-if="selected.importance"
                  :value="importanceLabel(selected.importance)"
                  :severity="importanceSeverity(selected.importance)"
                />
                <span v-if="selected.first_chapter" class="chapter-range">
                  Cap. {{ selected.first_chapter }}
                  <template v-if="selected.last_chapter && selected.last_chapter !== selected.first_chapter">
                    – {{ selected.last_chapter }}
                  </template>
                </span>
              </div>
            </div>
          </div>

          <!-- Detail tabs -->
          <TabView v-model:activeIndex="detailTab" class="detail-tabs">
            <!-- Info -->
            <TabPanel header="Info">
              <div class="info-section">
                <div v-if="selected.aliases?.length" class="info-block">
                  <label>Aliases:</label>
                  <span>{{ selected.aliases.join(', ') }}</span>
                </div>
                <div v-if="selected.description" class="info-block">
                  <label>Descripción:</label>
                  <p>{{ selected.description }}</p>
                </div>
                <div class="info-stats">
                  <span><strong>{{ selected.mention_count }}</strong> menciones</span>
                  <span><strong>{{ selected.chapters_present?.length || 0 }}</strong> capítulos</span>
                </div>
                <div v-if="selected.vital_status" class="info-block">
                  <label>Estado vital:</label>
                  <Tag
                    :value="selected.vital_status.status === 'dead' ? 'Fallecido' : selected.vital_status.status === 'alive' ? 'Vivo' : 'Desconocido'"
                    :severity="selected.vital_status.status === 'dead' ? 'danger' : 'success'"
                  />
                  <span v-if="selected.vital_status.death_chapter" class="death-info">
                    (Cap. {{ selected.vital_status.death_chapter }})
                  </span>
                </div>
              </div>
            </TabPanel>

            <!-- Attributes -->
            <TabPanel header="Atributos">
              <div v-if="!Object.keys(selected.attributes || {}).length" class="empty-section">
                Sin atributos extraídos.
              </div>
              <div v-else class="attributes-section">
                <div v-for="(attrs, category) in selected.attributes" :key="category" class="attr-category">
                  <h4 class="attr-category-title">{{ category }}</h4>
                  <div v-for="(attr, idx) in attrs" :key="idx" class="attr-item">
                    <span class="attr-key">{{ attr.key }}:</span>
                    <span class="attr-value">{{ attr.value }}</span>
                    <span v-if="attr.confidence" class="attr-confidence">
                      {{ (attr.confidence * 100).toFixed(0) }}%
                    </span>
                    <span v-if="attr.chapter" class="attr-chapter">Cap. {{ attr.chapter }}</span>
                    <p v-if="attr.source_text" class="attr-source">"{{ attr.source_text }}"</p>
                  </div>
                </div>
              </div>
            </TabPanel>

            <!-- Relationships -->
            <TabPanel header="Relaciones">
              <div v-if="!selected.relationships?.length" class="empty-section">
                Sin relaciones detectadas.
              </div>
              <div v-else class="relationships-section">
                <div v-for="(rel, idx) in selected.relationships" :key="idx" class="rel-item">
                  <div class="rel-header">
                    <span
                      class="rel-entity-link"
                      @click="navigateToEntity(rel.related_entity_id)"
                    >
                      {{ rel.related_entity_name }}
                    </span>
                    <Tag :value="rel.relation_type" severity="info" />
                    <Tag
                      v-if="rel.valence"
                      :value="rel.valence"
                      :severity="valenceSeverity(rel.valence)"
                    />
                  </div>
                  <p v-if="rel.description" class="rel-description">{{ rel.description }}</p>
                </div>
              </div>
            </TabPanel>

            <!-- Voice -->
            <TabPanel v-if="selected.voice_profile" header="Voz">
              <div class="voice-section">
                <div v-for="(val, key) in selected.voice_profile" :key="key" class="voice-metric">
                  <span class="voice-key">{{ formatMetricKey(key as string) }}:</span>
                  <span class="voice-value">
                    {{ typeof val === 'number' ? val.toFixed(2) : val }}
                  </span>
                </div>
              </div>
            </TabPanel>

            <!-- Knowledge -->
            <TabPanel v-if="selected.knowledge_summary" header="Conocimiento">
              <div class="knowledge-section">
                <pre class="knowledge-content">{{ JSON.stringify(selected.knowledge_summary, null, 2) }}</pre>
              </div>
            </TabPanel>
          </TabView>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import { apiUrl } from '@/config/api'

interface BibleEntry {
  entity_id: number
  canonical_name: string
  entity_type: string
  importance: string
  aliases: string[]
  description: string
  mention_count: number
  first_chapter: number | null
  last_chapter: number | null
  chapters_present: number[]
  attributes: Record<string, Array<{ key: string; value: string; confidence: number; chapter: number | null; source_text: string }>>
  relationships: Array<{ related_entity_id: number; related_entity_name: string; relation_type: string; strength: string; valence: string; description: string; direction: string }>
  vital_status: { status: string; death_chapter: number | null; confidence: number } | null
  voice_profile: Record<string, any> | null
  emotional_arc: Record<string, any> | null
  knowledge_summary: Record<string, any> | null
  user_notes: string
}

interface StoryBible {
  project_id: number
  project_name: string
  entries: BibleEntry[]
  stats: { total_characters: number; total_locations: number; total_organizations: number; total_objects: number; total_other: number }
}

const props = defineProps<{
  projectId: number
}>()

const loading = ref(false)
const bible = ref<StoryBible | null>(null)
const selectedId = ref<number | null>(null)
const filterType = ref<string | null>(null)
const searchQuery = ref('')
const detailTab = ref(0)

const entityTypes = [
  { value: 'character', label: 'Personajes', icon: 'pi pi-user' },
  { value: 'location', label: 'Lugares', icon: 'pi pi-map-marker' },
  { value: 'organization', label: 'Organizaciones', icon: 'pi pi-building' },
  { value: 'object', label: 'Objetos', icon: 'pi pi-box' },
]

const typeMap: Record<string, string[]> = {
  character: ['CHARACTER', 'PERSON', 'PER'],
  location: ['LOCATION', 'LOC', 'GPE', 'PLACE'],
  organization: ['ORGANIZATION', 'ORG'],
  object: ['OBJECT', 'MISC'],
}

const typeCounts = computed(() => {
  if (!bible.value) return {}
  const counts: Record<string, number> = {}
  for (const t of entityTypes) {
    const allowed = typeMap[t.value] || []
    counts[t.value] = bible.value.entries.filter(e => allowed.includes(e.entity_type.toUpperCase())).length
  }
  return counts
})

const filteredEntries = computed(() => {
  if (!bible.value) return []
  let entries = bible.value.entries
  if (filterType.value) {
    const allowed = typeMap[filterType.value] || []
    entries = entries.filter(e => allowed.includes(e.entity_type.toUpperCase()))
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    entries = entries.filter(e =>
      e.canonical_name.toLowerCase().includes(q) ||
      e.aliases?.some(a => a.toLowerCase().includes(q))
    )
  }
  return entries
})

const selected = computed(() => {
  if (!selectedId.value || !bible.value) return null
  return bible.value.entries.find(e => e.entity_id === selectedId.value) || null
})

// Reset detail tab when selection changes
watch(selectedId, () => { detailTab.value = 0 })

function typeIcon(entityType: string): string {
  const upper = entityType.toUpperCase()
  if (['CHARACTER', 'PERSON', 'PER'].includes(upper)) return 'pi pi-user'
  if (['LOCATION', 'LOC', 'GPE', 'PLACE'].includes(upper)) return 'pi pi-map-marker'
  if (['ORGANIZATION', 'ORG'].includes(upper)) return 'pi pi-building'
  if (['OBJECT', 'MISC'].includes(upper)) return 'pi pi-box'
  return 'pi pi-circle'
}

function typeLabel(entityType: string): string {
  const upper = entityType.toUpperCase()
  if (['CHARACTER', 'PERSON', 'PER'].includes(upper)) return 'Personaje'
  if (['LOCATION', 'LOC', 'GPE', 'PLACE'].includes(upper)) return 'Lugar'
  if (['ORGANIZATION', 'ORG'].includes(upper)) return 'Organización'
  if (['OBJECT', 'MISC'].includes(upper)) return 'Objeto'
  return entityType
}

function importanceLabel(imp: string): string {
  const map: Record<string, string> = { protagonist: 'Protagonista', main: 'Principal', secondary: 'Secundario', minor: 'Menor', mentioned: 'Mencionado' }
  return map[imp] || imp
}

function importanceSeverity(imp: string): string {
  const map: Record<string, string> = { protagonist: 'danger', main: 'warn', secondary: 'info', minor: 'secondary', mentioned: 'secondary' }
  return map[imp] || 'secondary'
}

function valenceSeverity(v: string): string {
  if (v === 'positive') return 'success'
  if (v === 'negative') return 'danger'
  return 'secondary'
}

function formatMetricKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function navigateToEntity(entityId: number) {
  selectedId.value = entityId
}

async function loadBible() {
  loading.value = true
  try {
    const res = await fetch(`${apiUrl}/api/projects/${props.projectId}/story-bible`)
    const json = await res.json()
    if (json.success) {
      bible.value = json.data
      // Auto-select first entry
      if (json.data.entries?.length && !selectedId.value) {
        selectedId.value = json.data.entries[0].entity_id
      }
    }
  } catch (e) {
    console.error('Story Bible error:', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.story-bible-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  height: 100%;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tab-header h3 { margin: 0; display: flex; align-items: center; gap: 0.5rem; }
.tab-header .subtitle { margin: 0.25rem 0 0; color: var(--text-color-secondary); font-size: 0.85rem; }
.header-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
.type-filter { display: flex; gap: 0.25rem; }
.search-input { width: 180px; }

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem;
  color: var(--text-color-secondary);
}
.empty-state i { font-size: 2rem; }

/* Layout */
.bible-layout {
  display: flex;
  gap: 1rem;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* Sidebar */
.bible-sidebar {
  width: 280px;
  min-width: 220px;
  overflow-y: auto;
  border-right: 1px solid var(--surface-border);
  padding-right: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sidebar-empty { padding: 1rem; color: var(--text-color-secondary); text-align: center; }
.entity-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.entity-item:hover { background: var(--surface-hover); }
.entity-item.active { background: var(--highlight-bg); color: var(--highlight-text-color); }
.entity-icon { font-size: 1.1rem; opacity: 0.7; }
.entity-info { display: flex; flex-direction: column; min-width: 0; }
.entity-name { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.entity-meta { display: flex; align-items: center; gap: 0.35rem; font-size: 0.75rem; color: var(--text-color-secondary); }
.importance-tag { font-size: 0.65rem; padding: 0 0.3rem; }
.mention-count { white-space: nowrap; }

/* Detail panel */
.bible-detail {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}
.detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-color-secondary);
  gap: 0.5rem;
}
.detail-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.detail-type-icon { font-size: 1.5rem; opacity: 0.6; }
.detail-name { margin: 0; font-size: 1.3rem; }
.detail-subtitle { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem; }
.chapter-range { font-size: 0.85rem; color: var(--text-color-secondary); }

/* Info tab */
.info-section { display: flex; flex-direction: column; gap: 0.75rem; }
.info-block label { font-weight: 600; font-size: 0.85rem; display: block; margin-bottom: 0.25rem; }
.info-block p { margin: 0; }
.info-stats { display: flex; gap: 1.5rem; font-size: 0.9rem; }
.death-info { font-size: 0.85rem; color: var(--text-color-secondary); }

/* Attributes tab */
.attributes-section { display: flex; flex-direction: column; gap: 1rem; }
.attr-category-title { margin: 0 0 0.5rem; font-size: 0.95rem; text-transform: capitalize; border-bottom: 1px solid var(--surface-border); padding-bottom: 0.25rem; }
.attr-item { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem; padding: 0.3rem 0; }
.attr-key { font-weight: 600; font-size: 0.85rem; }
.attr-value { font-size: 0.85rem; }
.attr-confidence { font-size: 0.75rem; color: var(--text-color-secondary); }
.attr-chapter { font-size: 0.75rem; color: var(--text-color-secondary); }
.attr-source { font-size: 0.8rem; font-style: italic; color: var(--text-color-secondary); margin: 0.15rem 0 0; width: 100%; }

/* Relationships tab */
.relationships-section { display: flex; flex-direction: column; gap: 0.5rem; }
.rel-item { padding: 0.5rem; border-radius: 4px; background: var(--surface-ground); }
.rel-header { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.rel-entity-link { font-weight: 600; color: var(--primary-color); cursor: pointer; }
.rel-entity-link:hover { text-decoration: underline; }
.rel-description { font-size: 0.85rem; color: var(--text-color-secondary); margin: 0.25rem 0 0; }

/* Voice tab */
.voice-section { display: flex; flex-direction: column; gap: 0.3rem; }
.voice-metric { display: flex; gap: 0.5rem; font-size: 0.85rem; }
.voice-key { font-weight: 600; min-width: 200px; }

/* Knowledge tab */
.knowledge-content { font-size: 0.8rem; white-space: pre-wrap; background: var(--surface-ground); padding: 0.75rem; border-radius: 4px; }

/* Empty section */
.empty-section { padding: 1rem; text-align: center; color: var(--text-color-secondary); }

/* Tabs */
.detail-tabs { margin-top: 0.5rem; }
</style>
