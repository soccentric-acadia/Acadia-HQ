<script setup lang="ts">
// WebConfig schema-form port: descriptor -> form with client-side validation.
// Same contract as WebConfig's components/schema-form.js — adding a setting
// requires a schema entry, zero UI code.
import { computed, reactive, watch } from 'vue'
import { fieldOptions, validateValues, type SectionDescriptor } from '@/lib/sectionSchemas'
import WcField from '@/components/wc/WcField.vue'
import WcToggle from '@/components/wc/WcToggle.vue'

const props = defineProps<{
  descriptor: SectionDescriptor
  values: Record<string, unknown>
  disabled?: boolean
}>()

const emit = defineEmits<{ save: [values: Record<string, unknown>] }>()

const local = reactive<Record<string, unknown>>({})
const errors = reactive<Record<string, string>>({})

watch(
  () => props.values,
  (values) => {
    for (const group of props.descriptor.groups) {
      for (const field of group.fields) {
        local[field.id] = values[field.id] ?? (field.field_type === 'bool' ? false : '')
      }
    }
  },
  { immediate: true, deep: true },
)

const dirty = computed(() => {
  for (const group of props.descriptor.groups) {
    for (const field of group.fields) {
      if (local[field.id] !== (props.values[field.id] ?? (field.field_type === 'bool' ? false : '')))
        return true
    }
  }
  return false
})

function save() {
  const issues = validateValues(props.descriptor, local)
  for (const key of Object.keys(errors)) delete errors[key]
  Object.assign(errors, issues)
  if (Object.keys(issues).length) return
  emit('save', { ...local })
}

defineExpose({ dirty, save })
</script>

<template>
  <div class="form-grid">
    <template v-for="group in descriptor.groups" :key="group.id">
      <h3>{{ group.title }}</h3>
      <template v-for="field in group.fields" :key="field.id">
        <WcToggle
          v-if="field.field_type === 'bool'"
          :model-value="Boolean(local[field.id])"
          :label="field.title"
          :disabled="disabled"
          @update:model-value="local[field.id] = $event"
        />
        <WcField
          v-else
          :model-value="String(local[field.id] ?? '')"
          :label="field.title"
          :type="field.field_type === 'enum' ? 'select' : field.field_type === 'secret' ? 'password' : field.field_type === 'int' ? 'number' : 'text'"
          :options="field.field_type === 'enum' ? fieldOptions(field) : undefined"
          :help="field.help"
          :error="errors[field.id]"
          :disabled="disabled"
          @update:model-value="local[field.id] = $event"
        />
      </template>
    </template>
    <div class="form-actions">
      <button class="btn btn-primary" :disabled="disabled" @click="save">Save settings</button>
    </div>
  </div>
</template>