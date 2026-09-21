<script setup lang="ts">
// Configuration-backed "can" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="can" :device-id="deviceId" />
</template>
