<script setup lang="ts">
// WebConfig toggle (switch) port.
const model = defineModel<boolean>({ default: false })
defineProps<{ label?: string; disabled?: boolean }>()
</script>

<template>
  <label class="switch" :class="{ 'switch-disabled': disabled }">
    <input v-model="model" type="checkbox" :disabled="disabled" />
    <span class="switch-track"><span class="switch-thumb" /></span>
    <span v-if="label" class="switch-label">{{ label }}</span>
  </label>
</template>