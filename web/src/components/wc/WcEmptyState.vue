<script setup lang="ts">
// WebConfig empty-state port.
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="empty-state">
    <div class="empty-state-title">{{ title }}</div>
    <div v-if="subtitle" class="empty-state-sub">{{ subtitle }}</div>
  </div>
</template>