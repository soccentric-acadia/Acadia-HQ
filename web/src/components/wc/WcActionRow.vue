<script setup lang="ts">
// WebConfig action-list row port: titled, explained control row.
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="action-row">
    <div class="min-w-0">
      <div class="action-row-title">{{ title }}</div>
      <div v-if="subtitle" class="action-row-sub">{{ subtitle }}</div>
    </div>
    <slot />
  </div>
</template>