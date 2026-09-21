<script setup lang="ts">
// Configuration-backed "services" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="services" :device-id="deviceId" />
</template>
