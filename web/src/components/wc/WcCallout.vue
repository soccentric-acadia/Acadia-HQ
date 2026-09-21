<script setup lang="ts">
// WebConfig callout port: inline page-level notice.
import { AlertTriangle, Info } from 'lucide-vue-next'

withDefaults(defineProps<{ kind?: 'info' | 'warning' }>(), { kind: 'info' })
</script>

<template>
  <div class="callout" :class="kind === 'warning' ? 'callout-warning' : 'callout-info'">
    <AlertTriangle v-if="kind === 'warning'" />
    <Info v-else />
    <div><slot /></div>
  </div>
</template>