<script setup lang="ts">
// Updates — HQ operation catalog for device updates (WebConfig updates.js
// slot-management analog; rollout delivery runs through the command gateway).
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'
import { runDeviceCommand } from '@/lib/deviceCommands'
import type { Operation } from '@/lib/types'
import WcActionRow from '@/components/wc/WcActionRow.vue'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcConfirmDialog from '@/components/wc/WcConfirmDialog.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string }>()

// T-P20 (K10): activate / confirm / roll back an installed update.
const busy = ref(false)
const confirmRollback = ref(false)
const typed = ref('')

async function run(label: string, queue: () => ReturnType<typeof api.commands.reboot>) {
  busy.value = true
  await runDeviceCommand(props.deviceId, label, queue)
  busy.value = false
}

function rollback() {
  const word = typed.value
  typed.value = ''
  return run('Rollback', () => api.commands.rollbackUpdate(props.deviceId, word))
}

// Only operations still waiting on their device contract are flagged.
const awaiting = (op: Operation) => op.integration_status?.startsWith('awaiting') ?? false

const operations = ref<Operation[]>([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    operations.value = (await api.operations.list()).items
  } catch {
    error.value = 'Could not load the operation catalog.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="3" />
  </div>
  <div v-else class="page-surface">
    <WcCard title="Update operations" subtitle="Operations HQ can deliver to this device through the command gateway.">
      <div v-if="error" class="error-text">{{ error }}</div>
      <template v-else>
        <div class="stack">
          <div v-for="op in operations" :key="op.name" class="row" style="justify-content: space-between">
            <div>
              <div class="action-row-title"><code>{{ op.name }}</code></div>
              <div class="action-row-sub">{{ op.description }}</div>
            </div>
            <span
              class="badge"
              :class="awaiting(op) ? 'badge-warning' : 'badge-success'"
            >
              {{ awaiting(op) ? 'awaiting contract' : 'available' }}
            </span>
          </div>
        </div>
      </template>
    </WcCard>

    <WcCard title="Activate installed update" subtitle="After an update is installed to the inactive slot.">
      <div class="action-list">
        <WcActionRow
          title="Reboot to apply"
          subtitle="Tryboot into the new slot. Firmware falls back to the old slot if it never boots."
        >
          <button class="btn btn-outline" :disabled="busy" @click="run('Reboot to apply', () => api.commands.rebootToApply(deviceId))">
            Reboot to apply
          </button>
        </WcActionRow>
        <WcActionRow
          title="Confirm update"
          subtitle="Mark the running slot good. The device also confirms automatically when its health check passes."
        >
          <button class="btn btn-outline" :disabled="busy" @click="run('Confirm update', () => api.commands.confirmUpdate(deviceId))">
            Confirm
          </button>
        </WcActionRow>
        <WcActionRow title="Roll back" subtitle="Return to the previous slot and reboot.">
          <button class="btn btn-destructive-outline" :disabled="busy" @click="confirmRollback = true">
            Roll back
          </button>
        </WcActionRow>
      </div>
    </WcCard>

    <WcCallout kind="info">
      Commands queue durably and run when the device next connects. Installing an artifact is on
      the Remote updates page.
    </WcCallout>

    <WcConfirmDialog
      v-model:open="confirmRollback"
      title="Roll back to the previous slot?"
      description="Type ROLLBACK to confirm. The device reboots into the previous image."
      confirm-label="Roll back"
      destructive
      @confirm="rollback"
    >
      <input v-model="typed" class="input" placeholder="ROLLBACK" aria-label="Type ROLLBACK" />
    </WcConfirmDialog>
  </div>
</template>