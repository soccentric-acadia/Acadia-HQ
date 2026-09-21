<script setup lang="ts">
// Configuration-backed "ssh" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="ssh" :device-id="deviceId" />
</template>
