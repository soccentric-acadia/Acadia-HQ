<script setup lang="ts">
// WebConfig field port: label + input/select + help + error.
import { computed, useAttrs } from 'vue'

const props = defineProps<{
  label: string
  type?: 'text' | 'password' | 'number' | 'select'
  help?: string
  error?: string
  placeholder?: string
  options?: { value: string; label?: string }[]
}>()

const model = defineModel<string | number>({ default: '' })
const attrs = useAttrs()

const isSelect = computed(() => props.type === 'select')
const inputType = computed(() =>
  props.type === 'password' ? 'password' : props.type === 'number' ? 'number' : 'text',
)
</script>

<template>
  <label class="field">
    <span class="field-label">{{ label }}</span>
    <select v-if="isSelect" v-model="model" class="input">
      <option v-for="o in options ?? []" :key="o.value" :value="o.value">
        {{ o.label ?? o.value }}
      </option>
    </select>
    <input
      v-else
      v-model="model"
      :type="inputType"
      :placeholder="placeholder"
      class="input"
      v-bind="attrs"
    />
    <span v-if="error" class="field-error">{{ error }}</span>
    <span v-else-if="help" class="field-help">{{ help }}</span>
  </label>
</template>