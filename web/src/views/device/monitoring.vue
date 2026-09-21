<script setup lang="ts">
// Monitoring — per-metric tiles with rolling sparkline history plus the HQ
// health factor breakdown (WebConfig monitoring.js composition).
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { DeviceHealth } from '@/lib/types'
import WcCard from '@/components/wc/WcCard.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'
import WcSparkline from '@/components/wc/WcSparkline.vue'

const props = defineProps<{ deviceId: string }>()

interface Point {
  recorded_at: string
  value: number
}

const series = ref<Record<string, Point[]>>({})
const health = ref<DeviceHealth | null>(null)
const loading = ref(true)
const error = ref('')
const live = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const entries = ref<[string, Point[]][]>([])

function refreshEntries() {
  entries.value = Object.entries(series.value)
}

async function load() {
  try {
    series.value = await api.devices.telemetry(props.deviceId)
    live.value = true
    refreshEntries()
  } catch {
    live.value = false
    error.value = 'Could not load device metrics.'
  } finally {
    loading.value = false
  }
}

async function loadHealth() {
  try {
    health.value = await api.devices.health(props.deviceId)
  } catch {
    /* health is best-effort here */
  }
}

function recent(points: Point[], count = 30): number[] {
  return points.slice(-count).map((p) => p.value)
}

watch(() => props.deviceId, load)
onMounted(() => {
  loadHealth()
  load()
  timer = setInterval(() => {
    loadHealth()
    load()
  }, 15000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="4" />
  </div>
  <div v-else class="page-surface">
    <div class="row" style="justify-content: flex-end">
      <span class="live-dot" :class="{ live }" />
      <span class="muted" style="font-size: var(--text-sm)">{{ live ? 'Live (15s poll)' : 'Reconnecting…' }}</span>
    </div>

    <WcCard title="Metrics" subtitle="Values the device publishes to HQ, with recent history.">
      <div v-if="error" class="error-text">{{ error }}</div>
      <div v-else-if="entries.length === 0" class="muted" style="font-size: var(--text-sm)">
        No metrics reported by this device yet.
      </div>
      <div v-else class="card-grid">
        <div v-for="[metric, points] in entries" :key="metric" class="card" style="margin-bottom: 0">
          <div class="card-body">
            <h3>{{ metric }}</h3>
            <div class="tile-sub">Latest</div>
            <div class="tile-value">{{ points.at(-1)?.value ?? '—' }}</div>
            <WcSparkline :points="recent(points)" />
          </div>
        </div>
      </div>
    </WcCard>

    <WcCard title="Health factors" subtitle="Explainable inputs behind the HQ health score.">
      <div v-if="!health || health.factors.length === 0" class="muted" style="font-size: var(--text-sm)">
        No health factors reported.
      </div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Factor</th><th>Status</th><th>Penalty</th></tr>
          </thead>
          <tbody>
            <tr v-for="f in health.factors" :key="f.name">
              <td>{{ f.name }}</td>
              <td><span class="badge" :class="f.penalty > 0 ? 'badge-warning' : 'badge-success'">{{ f.status }}</span></td>
              <td>{{ f.penalty }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </WcCard>
  </div>
</template>