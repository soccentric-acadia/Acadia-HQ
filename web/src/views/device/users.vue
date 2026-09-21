<script setup lang="ts">
// Configuration-backed "users" section (schema-driven; see ConfigSection).
import ConfigSection from '@/views/device/ConfigSection.vue'

defineProps<{ deviceId: string }>()
</script>

<template>
  <ConfigSection section-id="users" :device-id="deviceId" />
</template>
