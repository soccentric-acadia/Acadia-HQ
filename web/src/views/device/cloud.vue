<script setup lang="ts">
// Configuration-backed "cloud" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="cloud" :device-id="deviceId" />
</template>
