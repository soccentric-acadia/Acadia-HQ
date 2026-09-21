<script setup lang="ts">
// Configuration-backed "leds" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="leds" :device-id="deviceId" />
</template>
