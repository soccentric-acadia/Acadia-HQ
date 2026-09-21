<script setup lang="ts">
// Configuration-backed "5g" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="5g" :device-id="deviceId" />
</template>
