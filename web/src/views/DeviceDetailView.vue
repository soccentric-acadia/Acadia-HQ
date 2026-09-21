<script setup lang="ts">
// Device detail shell — 1:1 WebConfig (Acadia-Configuration) app shell
// (task 008): fixed categorized sidebar, topbar with device identity and
// status, command palette (Ctrl+K), `g <key>` navigation chords, toast
// region. The selected section renders in the content column below the
// topbar, exactly like WebConfig's layout.css.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { LogOut, Menu, Search } from 'lucide-vue-next'
import { api } from '@/lib/api'
import type { Device, DeviceHealth } from '@/lib/types'
import { connectDeviceStatusSocket } from '@/lib/deviceStatusSocket'
import { DEVICE_SECTIONS, sectionsByCategory } from '@/lib/deviceSections'
import { useAuthStore } from '@/stores/auth'
import CommandPalette from '@/components/wc/CommandPalette.vue'
import WcToastRegion from '@/components/wc/WcToastRegion.vue'

const props = defineProps<{ id: string }>()

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

// Stable section lookup for sidebar/chords/palette.
const sectionById = Object.fromEntries(DEVICE_SECTIONS.map((s) => [s.id, s]))

// Active section follows the route so deep links (and back/forward) stay in
// sync with the sidebar highlight.
const activeSectionId = computed(() => {
  const id = String(route.params.section ?? 'overview')
  return sectionById[id] ? id : 'overview'
})

const device = ref<Device | null>(null)
const health = ref<DeviceHealth | null>(null)
const loading = ref(true)
const loadError = ref('')

const paletteOpen = ref(false)
const sidebarCollapsed = ref(false)
const sidebarOpen = ref(false) // mobile drawer

// Bumped when the palette's "Refresh section" action fires; part of the
// section component's key so the active section remounts and re-fetches.
const sectionNonce = ref(0)

const groups = sectionsByCategory(auth.hasRole('admin'))

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [d, h] = await Promise.all([api.devices.get(props.id), api.devices.health(props.id)])
    device.value = d
    health.value = h
  } catch {
    loadError.value = 'Device not found.'
  } finally {
    loading.value = false
  }
}

// Live presence: the shared device status socket pushes online/offline.
let closeSocket: (() => void) | null = null
onMounted(() => {
  load()
  closeSocket = connectDeviceStatusSocket((event) => {
    if (device.value && event.device_id === device.value.id) {
      device.value = { ...device.value, online: event.online, last_seen_at: event.last_seen_at }
    }
  })
  window.addEventListener('keydown', onChordKeydown)
})
onBeforeUnmount(() => {
  closeSocket?.()
  window.removeEventListener('keydown', onChordKeydown)
})

// WebConfig `g <key>` chords: press g, then the section key.
let chordPending = false
let chordTimer: ReturnType<typeof setTimeout> | null = null
function onChordKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  const typing =
    target &&
    (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
  if (typing || paletteOpen.value) return
  if (event.key === 'g' && !chordPending) {
    chordPending = true
    if (chordTimer) clearTimeout(chordTimer)
    chordTimer = setTimeout(() => (chordPending = false), 1200)
    return
  }
  if (chordPending) {
    const section = Object.values(sectionById).find((s) => s.key === event.key)
    chordPending = false
    if (chordTimer) clearTimeout(chordTimer)
    if (section) {
      event.preventDefault()
      navigate(section.id)
    }
  }
}

function navigate(sectionId: string) {
  router.push({ name: 'device-section', params: { id: props.id, section: sectionId } })
}

function onPaletteAction(actionId: string) {
  if (actionId === 'back-to-devices') router.push({ name: 'devices' })
  else if (actionId === 'refresh') sectionNonce.value++
}

watch(activeSectionId, () => {
  sidebarOpen.value = false
})

async function logout() {
  await auth.logout()
  router.push({ name: 'login' })
}

const onlineTone = () => (device.value?.online ? 'badge-success' : 'badge-destructive')
const healthTone = () => {
  const status = health.value?.status
  return status === 'healthy'
    ? 'badge-success'
    : status === 'degraded'
      ? 'badge-warning'
      : 'badge-destructive'
}
</script>

<template>
  <div class="device-shell">
    <div v-if="loading" class="page-loading"><div class="spinner" /></div>
    <div v-else-if="loadError" class="error-text" style="padding: var(--space-8)">
      {{ loadError }}
    </div>
    <div
      v-else-if="device"
      class="app-shell"
      :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-open': sidebarOpen }"
    >
      <!-- Sidebar (WebConfig layout.css) -->
      <aside class="sidebar" aria-label="Device sections">
        <nav class="sidebar-nav">
          <template v-for="[category, sections] in groups" :key="category">
            <div class="sidebar-section-label">{{ category }}</div>
            <RouterLink
              v-for="section in sections"
              :key="section.id"
              class="sidebar-link"
              :class="{ active: section.id === activeSectionId }"
              :to="{ name: 'device-section', params: { id: device.id, section: section.id } }"
              :aria-current="section.id === activeSectionId ? 'page' : undefined"
            >
              <component :is="section.icon" />
              <span class="label">{{ section.label }}</span>
            </RouterLink>
          </template>
        </nav>
      </aside>
      <div class="sidebar-scrim" @click="sidebarOpen = false" />

      <!-- Main column -->
      <div class="main-col">
        <header class="topbar">
          <div class="topbar-brand">
            <span class="logo-mark">A</span>
            <span class="brand-text">Acadia HQ</span>
          </div>
          <button
            class="btn btn-ghost btn-sm btn-icon sidebar-desktop-toggle"
            title="Collapse navigation"
            @click="sidebarCollapsed = !sidebarCollapsed"
          >
            <Menu />
          </button>
          <button
            class="btn btn-ghost btn-sm btn-icon sidebar-mobile-toggle"
            title="Open navigation"
            @click="sidebarOpen = true"
          >
            <Menu />
          </button>
          <div class="topbar-heading">
            <span class="page-title">{{ device.name }}</span>
          </div>
          <span class="badge" :class="onlineTone()">{{
            device.online ? 'Online' : 'Offline'
          }}</span>
          <span class="badge badge-info">{{ device.pairing_state }}</span>
          <span v-if="health" class="badge" :class="healthTone()">health {{ health.score }}</span>
          <div class="spacer" />
          <button
            type="button"
            class="btn btn-outline search-trigger"
            aria-label="Search pages and actions"
            @click="paletteOpen = true"
          >
            <span class="search-trigger-copy">
              <Search style="width: 15px; height: 15px" />
              <span class="search-trigger-label">Search pages and actions</span>
            </span>
            <kbd class="cmdk-hint-kbd">Ctrl K</kbd>
          </button>
          <RouterLink to="/" class="btn btn-ghost btn-sm" title="All devices">Devices</RouterLink>
          <button
            class="btn btn-ghost btn-sm btn-icon topbar-logout"
            title="Log out"
            @click="logout()"
          >
            <LogOut />
          </button>
        </header>

        <main class="content">
          <RouterView v-slot="{ Component }">
            <Transition name="wc-page" mode="out-in">
              <component
                :is="Component"
                :key="`${activeSectionId}-${sectionNonce}`"
                class="page-enter"
              />
            </Transition>
          </RouterView>
        </main>
      </div>

      <CommandPalette
        v-model:open="paletteOpen"
        :device-name="device.name"
        :admin="auth.hasRole('admin')"
        @navigate="navigate"
        @action="onPaletteAction"
      />
    </div>
    <WcToastRegion />
  </div>
</template>

<style scoped>
.device-shell {
  min-height: 100vh;
}

.topbar-heading .page-title {
  margin-right: var(--space-3);
}

.topbar-logout {
  color: var(--muted-foreground);
}

/* Section switch transition (WebConfig .page-enter). */
.wc-page-enter-active,
.wc-page-leave-active {
  transition:
    opacity var(--duration-normal) var(--ease),
    transform var(--duration-normal) var(--ease);
}
.wc-page-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.wc-page-leave-to {
  opacity: 0;
}
</style>
