<script setup lang="ts">
// Configuration-backed "mcu" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="mcu" :device-id="deviceId" />
</template>
