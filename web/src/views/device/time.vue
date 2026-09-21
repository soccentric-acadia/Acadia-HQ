<script setup lang="ts">
// Configuration-backed "time" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="time" :device-id="deviceId" />
</template>