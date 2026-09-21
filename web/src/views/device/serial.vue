<script setup lang="ts">
// Configuration-backed "serial" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="serial" :device-id="deviceId" />
</template>
