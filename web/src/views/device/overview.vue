<script setup lang="ts">
// Overview — device identity, health factors, and latest reported metrics
// (WebConfig overview.js composition ported to HQ data sources).
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { DeviceHealth } from '@/lib/types'
import WcCard from '@/components/wc/WcCard.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'
import WcSparkline from '@/components/wc/WcSparkline.vue'
import WcStatusDot from '@/components/wc/WcStatusDot.vue'

const props = defineProps<{ deviceId: string }>()

interface Point {
  recorded_at: string
  value: number
}

const device = ref<import('@/lib/types').Device | null>(null)
const health = ref<DeviceHealth | null>(null)
const loading = ref(true)
const error = ref('')

const metricEntries = ref<[string, Point[]][]>([])

function latest(points: Point[]): number | null {
  return points.at(-1)?.value ?? null
}

function recentValues(points: Point[], count = 30): number[] {
  return points.slice(-count).map((p) => p.value)
}

function fmtWhen(value: string | null): string {
  return value ? new Date(value).toLocaleString() : '—'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [d, h, s] = await Promise.all([
      api.devices.get(props.deviceId),
      api.devices.health(props.deviceId),
      api.devices.telemetry(props.deviceId),
    ])
    device.value = d
    health.value = h
    metricEntries.value = Object.entries(s).slice(0, 6)
  } catch {
    error.value = 'Could not load the device overview.'
  } finally {
    loading.value = false
  }
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="4" />
  </div>
  <div v-else-if="error" class="error-text">{{ error }}</div>
  <div v-else-if="device" class="page-surface">
    <div class="card-grid">
      <WcCard title="Connection" subtitle="Presence as reported by the HQ gateway.">
        <div class="row">
          <WcStatusDot :state="device.online ? 'ok' : 'bad'" />
          <span>{{ device.online ? 'Online' : 'Offline' }}</span>
          <span class="badge badge-info">{{ device.pairing_state }}</span>
        </div>
        <div class="tile-sub">Last seen: {{ fmtWhen(device.last_seen_at) }}</div>
      </WcCard>
      <WcCard title="Health" :subtitle="`HQ composite score: ${health?.score ?? '—'} (${health?.status ?? '—'}).`">
        <div v-if="health">
          <div class="tile-value">{{ health.score }}<span class="tile-sub" style="display: inline; margin-left: 6px">/ 100</span></div>
          <div v-for="f in health.factors" :key="f.name" class="row" style="margin-top: 6px">
            <span class="tile-sub">{{ f.name }}</span>
            <span class="badge" :class="f.penalty > 0 ? 'badge-warning' : 'badge-success'">{{ f.status }}</span>
          </div>
        </div>
      </WcCard>
      <WcCard title="Identity" subtitle="Hardware identity recorded at pairing.">
        <div class="stack">
          <div class="row"><span class="tile-sub" style="min-width: 110px">Serial</span><code>{{ device.serial ?? '—' }}</code></div>
          <div class="row"><span class="tile-sub" style="min-width: 110px">Board revision</span><code>{{ device.board_rev ?? '—' }}</code></div>
          <div class="row"><span class="tile-sub" style="min-width: 110px">Created</span><span>{{ fmtWhen(device.created_at) }}</span></div>
        </div>
      </WcCard>
    </div>

    <WcCard title="Latest metrics" subtitle="Most recent values the device published to HQ.">
      <div v-if="metricEntries.length === 0" class="muted" style="font-size: var(--text-sm)">
        No telemetry reported yet.
      </div>
      <div v-else class="card-grid">
        <div v-for="[metric, points] in metricEntries" :key="metric" class="card" style="margin-bottom: 0">
          <div class="card-body">
            <h3>{{ metric }}</h3>
            <div class="tile-value">{{ latest(points) ?? '—' }}</div>
            <WcSparkline :points="recentValues(points)" />
          </div>
        </div>
      </div>
    </WcCard>
  </div>
</template>