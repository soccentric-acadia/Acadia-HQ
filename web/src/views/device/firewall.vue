<script setup lang="ts">
// Configuration-backed "firewall" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="firewall" :device-id="deviceId" />
</template>
