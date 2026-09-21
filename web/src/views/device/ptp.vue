<script setup lang="ts">
// Configuration-backed "ptp" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="ptp" :device-id="deviceId" />
</template>
