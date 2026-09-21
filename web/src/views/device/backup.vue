<script setup lang="ts">
// Backup & Restore — queue on-device backups and restore prior ones through
// the command gateway (WebConfig backup.js composition).
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { Backup } from '@/lib/types'
import { toast } from '@/stores/toasts'
import WcActionRow from '@/components/wc/WcActionRow.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcConfirmDialog from '@/components/wc/WcConfirmDialog.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string }>()

const backups = ref<Backup[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const queuedNote = ref('')
const restoreTarget = ref<Backup | null>(null)

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.backups.list(props.deviceId)
    backups.value = res.items
  } catch {
    error.value = 'Could not load backups.'
  } finally {
    loading.value = false
  }
}

async function takeBackup() {
  busy.value = true
  try {
    const res = await api.backups.takeNow(props.deviceId)
    queuedNote.value = `Backup requested (command ${'command_id' in res ? String(res.command_id) : 'queued'}); the archive appears when the device uploads it.`
    toast('Backup requested.', 'success')
    await load()
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Backup request failed.', 'error')
  } finally {
    busy.value = false
  }
}

async function restore() {
  if (!restoreTarget.value) return
  busy.value = true
  try {
    await api.backups.restore(props.deviceId, restoreTarget.value.id)
    toast('Restore requested.', 'success')
    queuedNote.value = 'Restore command queued for delivery on the device\'s next heartbeat.'
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Restore request failed.', 'error')
  } finally {
    busy.value = false
    restoreTarget.value = null
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
    <p v-if="queuedNote" class="muted" style="font-size: var(--text-sm)">{{ queuedNote }}</p>

    <WcCard title="Backups" subtitle="Configuration and state archives the device has uploaded to HQ.">
      <div v-if="error" class="error-text">{{ error }}</div>
      <WcEmptyState
        v-else-if="backups.length === 0"
        title="No backups yet"
        subtitle="Take a backup to capture the current device configuration."
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Created</th><th>Size</th><th>Restored</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="b in backups" :key="b.id">
              <td>{{ new Date(b.created_at).toLocaleString() }}</td>
              <td><code>{{ fmtBytes(b.size_bytes) }}</code></td>
              <td>{{ b.restored_at ? new Date(b.restored_at).toLocaleString() : '—' }}</td>
              <td>
                <div class="table-actions">
                  <button
                    class="btn btn-destructive-outline btn-sm"
                    :disabled="busy"
                    @click="restoreTarget = b"
                  >
                    Restore
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-footer">
        <WcActionRow
          title="Take backup now"
          subtitle="Queue an on-device backup; the archive is uploaded to HQ when complete."
        >
          <button class="btn btn-primary btn-sm" :disabled="busy" @click="takeBackup">
            Take backup now
          </button>
        </WcActionRow>
      </div>
    </WcCard>

    <WcConfirmDialog
      :open="restoreTarget !== null"
      title="Restore this backup?"
      description="The device will replace its current configuration with the selected backup after the command is delivered."
      confirm-label="Restore"
      destructive
      @update:open="(v) => !v && (restoreTarget = null)"
      @confirm="restore"
    />
  </div>
</template>