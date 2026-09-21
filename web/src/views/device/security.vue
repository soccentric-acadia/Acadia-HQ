<script setup lang="ts">
// Configuration-backed "security" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="security" :device-id="deviceId" />
</template>
