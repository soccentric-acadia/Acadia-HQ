<script setup lang="ts">
// Configuration-backed "telemetry" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="telemetry" :device-id="deviceId" />
</template>
