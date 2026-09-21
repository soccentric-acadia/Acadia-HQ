<script setup lang="ts">
// WebConfig toast region port (bottom-right dark toasts).
import { X } from 'lucide-vue-next'
import { dismiss, useToasts } from '@/stores/toasts'

const { toasts } = useToasts()
</script>

<template>
  <Teleport to="body">
    <div class="toast-region" aria-live="polite">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="`toast-${t.kind}`">
        <span>{{ t.message }}</span>
        <button class="toast-dismiss" aria-label="Dismiss" @click="dismiss(t.id)">
          <X style="width: 14px; height: 14px" />
        </button>
      </div>
    </div>
  </Teleport>
</template>