<script setup lang="ts">
// Alarms — device-reported 4-byte alarms and their lifecycle (WebConfig
// alerts.js composition; HQ stores fired device alarms, threshold rule packs
// live in the fleet-wide Alarm Rules view).
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/lib/api'
import type { DeviceAlarm } from '@/lib/types'
import { toast } from '@/stores/toasts'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string }>()

const alarms = ref<DeviceAlarm[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)

function stateTone(state: string): string {
  return state === 'active'
    ? 'badge-destructive'
    : state === 'acknowledged'
      ? 'badge-warning'
      : 'badge-success'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.alarms.listForDevice(props.deviceId)
    alarms.value = res.items
  } catch {
    error.value = 'Could not load alarms.'
  } finally {
    loading.value = false
  }
}

async function act(fn: () => Promise<unknown>, message: string) {
  busy.value = true
  try {
    await fn()
    toast(message, 'success')
    await load()
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Action failed.', 'error')
  } finally {
    busy.value = false
  }
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="3" />
  </div>
  <div v-else class="page-surface">
    <WcCallout kind="info">
      Device alarms fire from threshold rules. Fleet-wide rule packs are managed under
      <RouterLink to="/alarm-rules" class="btn-link">Alarm Rules</RouterLink>.
    </WcCallout>

    <WcCard title="Alarm events" subtitle="Alarms this device has reported, newest first.">
      <div v-if="error" class="error-text">{{ error }}</div>
      <WcEmptyState
        v-else-if="alarms.length === 0"
        title="No alarms recorded"
        subtitle="No threshold alarms have fired on this device."
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Alarm code</th><th>Packed fields</th><th>State</th><th>Triggered</th><th>Resolved</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="a in alarms" :key="a.id">
              <td><code>{{ `0x${a.alarm_code.toString(16).padStart(8, '0')}` }}</code></td>
              <td class="muted">major {{ a.major_id }} · sub {{ a.sub_section }} · type {{ a.fault_type }} · sev {{ a.severity }}</td>
              <td><span class="badge" :class="stateTone(a.state)">{{ a.state }}</span></td>
              <td>{{ new Date(a.triggered_at).toLocaleString() }}</td>
              <td>{{ a.resolved_at ? new Date(a.resolved_at).toLocaleString() : '—' }}</td>
              <td>
                <div class="table-actions">
                  <button
                    v-if="a.state === 'active'"
                    class="btn btn-outline btn-sm"
                    :disabled="busy"
                    @click="act(() => api.alarms.acknowledgeDevice(props.deviceId, a.id), 'Alarm acknowledged on HQ and the device.')"
                  >
                    Acknowledge
                  </button>
                  <button
                    v-if="a.state !== 'resolved'"
                    class="btn btn-ghost btn-sm"
                    :disabled="busy"
                    @click="act(() => api.alarms.clear(props.deviceId, a.id), 'Alarm cleared on HQ and the device.')"
                  >
                    Clear
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WcCard>
  </div>
</template>