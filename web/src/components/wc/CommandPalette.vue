<script setup lang="ts">
// WebConfig command palette port (Ctrl/Cmd+K): filterable section navigation
// plus device actions, keyboard-driven (arrows + enter, esc to close).
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import { DEVICE_SECTIONS } from '@/lib/deviceSections'

const props = withDefaults(
  defineProps<{
    deviceName?: string
    /** When false, admin-only sections are hidden (mirrors the sidebar). */
    admin?: boolean
  }>(),
  { deviceName: undefined, admin: false },
)
const emit = defineEmits<{ navigate: [sectionId: string]; action: [actionId: string] }>()

const open = defineModel<boolean>('open', { default: false })
const query = ref('')
const activeIndex = ref(0)
const searchInput = ref<HTMLInputElement | null>(null)

interface PaletteItem {
  id: string
  label: string
  hint: string
  kind: 'section' | 'action'
}

const ACTIONS: PaletteItem[] = [
  { id: 'refresh', label: 'Refresh section', hint: 'Action', kind: 'action' },
  { id: 'back-to-devices', label: 'Back to all devices', hint: 'Action', kind: 'action' },
]

const items = computed<PaletteItem[]>(() => {
  const q = query.value.trim().toLowerCase()
  const sections = DEVICE_SECTIONS.filter((s) => props.admin || !s.adminOnly).map((s) => ({
    id: s.id,
    label: s.label,
    hint: `${s.category} · Section`,
    kind: 'section' as const,
  }))
  const all = [...sections, ...ACTIONS]
  if (!q) return all
  return all.filter(
    (item) => item.label.toLowerCase().includes(q) || item.hint.toLowerCase().includes(q),
  )
})

watch(items, () => {
  activeIndex.value = 0
})

watch(open, async (isOpen) => {
  if (isOpen) {
    query.value = ''
    activeIndex.value = 0
    await nextTick()
    searchInput.value?.focus()
  }
})

function select(item: PaletteItem) {
  open.value = false
  if (item.kind === 'section') emit('navigate', item.id)
  else emit('action', item.id)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % items.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + items.value.length) % items.value.length
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const item = items.value[activeIndex.value]
    if (item) select(item)
  } else if (event.key === 'Escape') {
    open.value = false
  }
}

// Global Ctrl/Cmd+K toggle.
function onGlobalKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    open.value = !open.value
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))

defineExpose({ onKeydown })
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-scrim cmdk-scrim" @click.self="open = false">
      <div
        class="modal cmdk-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Search pages and actions"
        @keydown="onKeydown"
      >
        <div class="modal-body">
          <div class="cmdk-search-row">
            <Search style="width: 16px; height: 16px" />
            <input
              ref="searchInput"
              v-model="query"
              class="cmdk-input"
              :placeholder="deviceName ? `Search ${deviceName} pages and actions` : 'Search pages and actions'"
            />
            <kbd class="cmdk-hint-kbd">Esc</kbd>
          </div>
          <div class="cmdk-list">
            <div
              v-for="(item, i) in items"
              :key="item.kind + item.id"
              class="cmdk-item"
              :class="{ active: i === activeIndex }"
              @click="select(item)"
              @mousemove="activeIndex = i"
            >
              <span class="cmdk-item-text">{{ item.label }}</span>
              <span class="cmdk-item-hint">{{ item.hint }}</span>
            </div>
            <div v-if="items.length === 0" class="cmdk-empty">No matching pages or actions.</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>