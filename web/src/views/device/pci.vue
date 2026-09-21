<script setup lang="ts">
// Configuration-backed "pci" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="pci" :device-id="deviceId" />
</template>
