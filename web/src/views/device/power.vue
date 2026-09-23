<script setup lang="ts">
// Power — reboot/shutdown (WebConfig power.js), delivered as T-P20 command
// kinds. The device acknowledges first and acts ~5 s later, so the result
// always reaches HQ before the unit goes down.
import { ref } from 'vue'
import { api } from '@/lib/api'
import { runDeviceCommand } from '@/lib/deviceCommands'
import WcActionRow from '@/components/wc/WcActionRow.vue'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcConfirmDialog from '@/components/wc/WcConfirmDialog.vue'

const props = defineProps<{ deviceId: string }>()

const busy = ref(false)
const confirmReboot = ref(false)
const confirmShutdown = ref(false)
const typed = ref('')

async function reboot() {
  busy.value = true
  await runDeviceCommand(props.deviceId, 'Reboot', () => api.commands.reboot(props.deviceId))
  busy.value = false
}

async function shutdown() {
  busy.value = true
  const word = typed.value
  typed.value = ''
  await runDeviceCommand(props.deviceId, 'Shutdown', () =>
    api.commands.shutdown(props.deviceId, word),
  )
  busy.value = false
}
</script>

<template>
  <div class="page-surface">
    <WcCard title="Power controls" subtitle="Restart or power off the device.">
      <div class="action-list">
        <WcActionRow title="Reboot" subtitle="Restart the device. It reconnects to HQ after boot.">
          <button class="btn btn-outline" :disabled="busy" @click="confirmReboot = true">Reboot</button>
        </WcActionRow>
        <WcActionRow
          title="Shut down"
          subtitle="Power the device off. HQ cannot turn it back on; someone must power-cycle it on site."
        >
          <button class="btn btn-destructive-outline" :disabled="busy" @click="confirmShutdown = true">
            Shut down
          </button>
        </WcActionRow>
      </div>
    </WcCard>
    <WcCallout kind="info">
      Commands are queued durably: an offline device runs them when it next connects, until the
      command expires.
    </WcCallout>

    <WcConfirmDialog
      v-model:open="confirmReboot"
      title="Reboot device?"
      description="The device restarts about five seconds after it acknowledges the command."
      confirm-label="Reboot"
      @confirm="reboot"
    />
    <WcConfirmDialog
      v-model:open="confirmShutdown"
      title="Shut down device?"
      description="Type SHUTDOWN to confirm. HQ cannot power the device back on."
      confirm-label="Shut down"
      destructive
      @confirm="shutdown"
    >
      <input v-model="typed" class="input" placeholder="SHUTDOWN" aria-label="Type SHUTDOWN" />
    </WcConfirmDialog>
  </div>
</template>
