<script setup lang="ts">
// Logs — log bundles the device has uploaded to HQ (WebConfig logs.js
// composition; journal streaming arrives with the device contract).
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { LogBundle } from '@/lib/types'
import { toast } from '@/stores/toasts'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string }>()

const bundles = ref<LogBundle[]>([])
const loading = ref(true)
const error = ref('')

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.logs.list(props.deviceId)
    bundles.value = res.items
  } catch {
    error.value = 'Could not load log bundles.'
  } finally {
    loading.value = false
  }
}

async function download(bundle: LogBundle) {
  try {
    const { download_url } = await api.logs.downloadUrl(props.deviceId, bundle.id)
    window.open(download_url, '_blank')
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Download failed.', 'error')
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
    <WcCard title="Log bundles" subtitle="Diagnostics archives the device has uploaded to HQ.">
      <div v-if="error" class="error-text">{{ error }}</div>
      <WcEmptyState
        v-else-if="bundles.length === 0"
        title="No log bundles yet"
        subtitle="Bundles uploaded by the device appear here for download."
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Time range</th><th>Uploaded</th><th>Size</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="b in bundles" :key="b.id">
              <td class="muted">
                {{ new Date(b.time_range_start).toLocaleString() }} –
                {{ new Date(b.time_range_end).toLocaleString() }}
              </td>
              <td>{{ new Date(b.uploaded_at).toLocaleString() }}</td>
              <td><code>{{ fmtBytes(b.size_bytes) }}</code></td>
              <td>
                <div class="table-actions">
                  <button class="btn btn-outline btn-sm" @click="download(b)">Download</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WcCard>

    <WcCallout kind="info">
      Live journal streaming and log storage configuration run on-device in WebConfig; they become
      available here once the device configuration contract is connected.
    </WcCallout>
  </div>
</template>