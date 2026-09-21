<script setup lang="ts">
// Faults — device-reported faults (WebConfig faults.js composition: a single
// read-only table of current fault conditions).
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { Fault } from '@/lib/types'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string }>()

const faults = ref<Fault[]>([])
const loading = ref(true)
const error = ref('')

function severityTone(sev: string): string {
  return sev === 'critical' ? 'badge-destructive' : sev === 'warn' ? 'badge-warning' : 'badge-neutral'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.faults.list(props.deviceId)
    faults.value = res.items
  } catch {
    error.value = 'Could not load faults.'
  } finally {
    loading.value = false
  }
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="3" />
  </div>
  <div v-else-if="error" class="error-text">{{ error }}</div>
  <WcCard v-else title="Faults" subtitle="Fault conditions reported by the device.">
    <WcEmptyState
      v-if="faults.length === 0"
      title="No faults reported"
      subtitle="The device has not raised any faults."
    />
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr><th>Severity</th><th>Code</th><th>Message</th><th>Raised</th><th>State</th></tr>
        </thead>
        <tbody>
          <tr v-for="f in faults" :key="f.id">
            <td><span class="badge" :class="severityTone(f.severity)">{{ f.severity }}</span></td>
            <td><code>{{ f.code }}</code></td>
            <td>{{ f.message || '—' }}</td>
            <td>{{ new Date(f.raised_at).toLocaleString() }}</td>
            <td>
              <span class="row">
                <span class="dot" :class="f.cleared_at ? 'dot-ok' : 'dot-bad'" />
                {{ f.cleared_at ? `Cleared ${new Date(f.cleared_at).toLocaleString()}` : 'Active' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </WcCard>
</template>