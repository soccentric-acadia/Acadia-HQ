<script setup lang="ts">
// WebConfig StatusDot port.
withDefaults(defineProps<{ state?: 'ok' | 'warn' | 'bad' | 'unknown' }>(), {
  state: 'unknown',
})
</script>

<template>
  <span class="dot" :class="`dot-${state}`" />
</template>