<script setup lang="ts">
// Configuration-backed "wireless" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="wireless" :device-id="deviceId" />
</template>
