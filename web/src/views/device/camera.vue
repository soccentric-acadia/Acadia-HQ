<script setup lang="ts">
// Configuration-backed "camera" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="camera" :device-id="deviceId" />
</template>
