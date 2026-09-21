<script setup lang="ts">
// Configuration-backed "system" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="system" :device-id="deviceId" />
</template>
