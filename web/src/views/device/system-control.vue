<script setup lang="ts">
// System Control — destructive lifecycle controls (WebConfig
// system-control.js composition: confirm-guarded reset actions).
import { ref } from 'vue'
import { api } from '@/lib/api'
import { toast } from '@/stores/toasts'
import WcActionRow from '@/components/wc/WcActionRow.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcConfirmDialog from '@/components/wc/WcConfirmDialog.vue'

const props = defineProps<{ deviceId: string }>()

const confirmKind = ref<'reset' | 'disable' | null>(null)
const busy = ref(false)

async function perform() {
  if (!confirmKind.value) return
  busy.value = true
  try {
    if (confirmKind.value === 'reset') {
      await api.devices.factoryReset(props.deviceId)
      toast('Factory reset requested.', 'success')
    } else {
      await api.devices.disable(props.deviceId)
      toast('Device disabled.', 'success')
    }
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Action failed.', 'error')
  } finally {
    busy.value = false
    confirmKind.value = null
  }
}
</script>

<template>
  <WcCard
    title="System controls"
    subtitle="These actions change persistent device state and are delivered through the command gateway."
  >
    <div class="action-list">
      <WcActionRow
        title="Factory reset"
        subtitle="Erase configuration and return the device to its installed defaults. This cannot be undone by HQ."
      >
        <button class="btn btn-destructive-outline" :disabled="busy" @click="confirmKind = 'reset'">
          Factory reset
        </button>
      </WcActionRow>
      <WcActionRow
        title="Disable device"
        subtitle="HQ will refuse this device's connection immediately, even with a valid credential."
      >
        <button class="btn btn-destructive-outline" :disabled="busy" @click="confirmKind = 'disable'">
          Disable device
        </button>
      </WcActionRow>
    </div>

    <WcConfirmDialog
      :open="confirmKind === 'reset'"
      title="Factory reset device?"
      description="This erases all settings and returns the device to its installed defaults. The device will need to be re-paired."
      confirm-label="Factory reset"
      destructive
      @update:open="(v) => !v && confirmKind === 'reset' && (confirmKind = null)"
      @confirm="perform"
    />
    <WcConfirmDialog
      :open="confirmKind === 'disable'"
      title="Disable this device?"
      description="HQ will refuse this device's connection immediately, even with a valid credential."
      confirm-label="Disable"
      destructive
      @update:open="(v) => !v && confirmKind === 'disable' && (confirmKind = null)"
      @confirm="perform"
    />
  </WcCard>
</template>