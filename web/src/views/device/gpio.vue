<script setup lang="ts">
// Configuration-backed "gpio" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="gpio" :device-id="deviceId" />
</template>
