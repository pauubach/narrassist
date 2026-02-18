<template>
  <Dialog
    :visible="visible"
    :header="isEditing ? 'Editar Colección' : 'Nueva Colección'"
    :modal="true"
    :closable="true"
    :style="{ width: '450px' }"
    @update:visible="$emit('update:visible', $event)"
    @hide="$emit('hide')"
  >
    <div class="dialog-form">
      <div class="field">
        <label for="collection-name">Nombre</label>
        <InputText
          id="collection-name"
          v-model="name"
          placeholder="Ej: Saga del Reino Perdido"
          class="w-full"
          autofocus
          @keydown.enter="handleSave"
        />
      </div>
      <div class="field">
        <label for="collection-desc">Descripción</label>
        <Textarea
          id="collection-desc"
          v-model="description"
          placeholder="Descripción opcional de la colección..."
          rows="3"
          class="w-full"
        />
      </div>
    </div>

    <template #footer>
      <Button label="Cancelar" text @click="$emit('update:visible', false)" />
      <Button
        :label="isEditing ? 'Guardar' : 'Crear'"
        icon="pi pi-check"
        :disabled="!name.trim()"
        @click="handleSave"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import type { Collection } from '@/types'

const props = defineProps<{
  visible: boolean
  collection?: Collection | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  save: [name: string, description: string]
  hide: []
}>()

const name = ref('')
const description = ref('')

const isEditing = computed(() => !!props.collection)

watch(() => props.visible, (val) => {
  if (val) {
    name.value = props.collection?.name ?? ''
    description.value = props.collection?.description ?? ''
  }
})

function handleSave() {
  if (!name.value.trim()) return
  emit('save', name.value.trim(), description.value.trim())
}
</script>

<style scoped>
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field label {
  font-weight: 600;
  font-size: 0.875rem;
}
</style>
