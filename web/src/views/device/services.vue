<script setup lang="ts">
// Services — MQTT settings (configuration-backed, services.mqtt) plus unit
// control through the T-P20 `service.control` command. The device only acts
// on units in its board-manifest service allowlist.
import { ref } from 'vue'
import { api } from '@/lib/api'
import { runDeviceCommand } from '@/lib/deviceCommands'
import type { ServiceAction } from '@/lib/types'
import ConfigSection from '@/views/device/ConfigSection.vue'
import WcCard from '@/components/wc/WcCard.vue'

const props = defineProps<{ deviceId: string }>()

const ACTIONS: ServiceAction[] = ['start', 'stop', 'restart', 'enable', 'disable']
const unit = ref('')
const busy = ref(false)

async function control(action: ServiceAction) {
  busy.value = true
  await runDeviceCommand(props.deviceId, `${action} ${unit.value}`, () =>
    api.commands.serviceControl(props.deviceId, unit.value, action),
  )
  busy.value = false
}
</script>

<template>
  <div class="page-surface">
    <WcCard title="Service control" subtitle="Start, stop or restart an allowlisted device unit.">
      <div class="stack">
        <input
          v-model="unit"
          class="input"
          placeholder="e.g. sshd.service"
          aria-label="Unit name"
          pattern="[A-Za-z0-9@._+-]+"
        />
        <div class="row">
          <button
            v-for="a in ACTIONS"
            :key="a"
            class="btn btn-outline btn-sm"
            :disabled="busy || !unit"
            @click="control(a)"
          >
            {{ a }}
          </button>
        </div>
      </div>
    </WcCard>
    <ConfigSection section-id="services" :device-id="deviceId" />
  </div>
</template>
