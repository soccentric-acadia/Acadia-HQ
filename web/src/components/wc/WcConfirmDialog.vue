<script setup lang="ts">
// WebConfig confirmDialog port: destructive-capable confirmation modal.
const open = defineModel<boolean>('open', { default: false })

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    confirmLabel?: string
    cancelLabel?: string
    destructive?: boolean
  }>(),
  { confirmLabel: 'Confirm', cancelLabel: 'Cancel', destructive: false },
)

const emit = defineEmits<{ confirm: [] }>()

function close() {
  open.value = false
}

function confirm() {
  emit('confirm')
  close()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="wc-fade">
      <div v-if="open" class="modal-scrim" @click.self="close">
        <div class="modal" role="alertdialog" aria-modal="true" :aria-label="props.title">
          <div class="modal-header">
            <h2 class="text-base font-semibold" style="font-size: var(--text-lg)">{{ props.title }}</h2>
          </div>
          <div class="modal-body">
            <p v-if="description" class="muted" style="font-size: var(--text-sm)">{{ description }}</p>
            <slot />
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost btn-sm" @click="close">{{ cancelLabel }}</button>
            <button
              class="btn btn-sm"
              :class="destructive ? 'btn-destructive' : 'btn-primary'"
              @click="confirm"
            >
              {{ confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.wc-fade-enter-active,
.wc-fade-leave-active {
  transition: opacity var(--duration-fast, 120ms) ease;
}
.wc-fade-enter-from,
.wc-fade-leave-to {
  opacity: 0;
}
</style>