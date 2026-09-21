<script setup lang="ts">
// WebConfig skeleton port: shimmering placeholder blocks.
withDefaults(defineProps<{ lines?: number }>(), { lines: 3 })
</script>

<template>
  <div class="card">
    <div class="card-body space-y-3">
      <div v-for="i in lines" :key="i" class="skeleton h-4" :style="{ width: `${100 - i * 12}%` }" />
    </div>
  </div>
</template>