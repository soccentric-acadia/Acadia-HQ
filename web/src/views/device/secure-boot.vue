<script setup lang="ts">
// Configuration-backed "secure-boot" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="secure-boot" :device-id="deviceId" />
</template>
