<script setup lang="ts">
// Configuration-backed "display" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="display" :device-id="deviceId" />
</template>
