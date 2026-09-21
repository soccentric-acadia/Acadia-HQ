<script setup lang="ts">
// Configuration-backed "wired" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="wired" :device-id="deviceId" />
</template>
