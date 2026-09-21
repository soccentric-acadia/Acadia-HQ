<script setup lang="ts">
// Configuration-backed "ntp" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="ntp" :device-id="deviceId" />
</template>
