<script setup lang="ts">
// ConfigSection — shared renderer for configuration-backed device sections
// (task 008 phase 4). Queues `configuration.read` on mount, polls the durable
// command result, renders the schema-driven form when the device reports
// values, and states precisely what is pending while
// `integration_status === 'awaiting_configuration_contract'`.
//
// WebConfig parity: same callout/empty-state/button compositions; the
// unsaved-changes guard (WebConfig core/dirty-guard.js) blocks navigation.
import { computed, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { RefreshCw } from 'lucide-vue-next'
import {
  CONFIG_CONTRACT_PENDING,
  readConfiguration,
  writeConfiguration,
  type ConfigurationCommandOutcome,
} from '@/lib/configCommands'
import { SECTION_DESCRIPTORS, type SectionDescriptor } from '@/lib/sectionSchemas'
import { toast } from '@/stores/toasts'
import SchemaForm from '@/components/wc/SchemaForm.vue'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcConfirmDialog from '@/components/wc/WcConfirmDialog.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string; sectionId: string }>()

const loading = ref(true)
const outcome = ref<ConfigurationCommandOutcome | null>(null)
const saving = ref(false)
const leaveConfirmOpen = ref(false)
let pendingLeave: (() => void) | null = null

const formRef = ref<InstanceType<typeof SchemaForm> | null>(null)

const descriptor = computed<SectionDescriptor | undefined>(
  () => SECTION_DESCRIPTORS[props.sectionId],
)
const contractPending = computed(
  () => outcome.value?.command.integration_status === CONFIG_CONTRACT_PENDING,
)
const values = computed(() => outcome.value?.values ?? null)
const commandError = computed(() => {
  const cmd = outcome.value?.command
  if (!cmd) return null
  if (cmd.state === 'failed') return cmd.error ?? 'The device rejected the command.'
  if (cmd.state === 'expired') return 'The command expired before the device acknowledged it.'
  return null
})
const hasDescriptor = computed(() => descriptor.value !== undefined)

async function read() {
  loading.value = true
  try {
    outcome.value = await readConfiguration(props.deviceId)
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Could not queue the configuration read.', 'error')
  } finally {
    loading.value = false
  }
}

async function save(valuesToWrite: Record<string, unknown>) {
  saving.value = true
  try {
    await writeConfiguration(props.deviceId, valuesToWrite)
    toast('Configuration write queued for the device.', 'success')
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Could not queue the configuration write.', 'error')
  } finally {
    saving.value = false
  }
}

// Unsaved-changes guard (WebConfig dirty-guard parity): covers both section
// switches (param update) and navigation away from the device shell.
onBeforeRouteLeave((_to, _from, next) => {
  if (!formRef.value?.dirty) {
    next()
    return
  }
  pendingLeave = () => next()
  leaveConfirmOpen.value = true
})

onBeforeRouteUpdate((_to, _from, next) => {
  if (!formRef.value?.dirty) {
    next()
    return
  }
  pendingLeave = () => next()
  leaveConfirmOpen.value = true
})

function discardAndLeave() {
  leaveConfirmOpen.value = false
  pendingLeave?.()
  pendingLeave = null
}

watch(() => props.deviceId, read)
onMounted(read)
</script>

<template>
  <div class="page-surface">
    <div v-if="loading"><WcSkeleton :lines="3" /></div>

    <template v-else>
      <WcCallout v-if="contractPending" kind="warning">
        <strong>Awaiting the device configuration contract.</strong>
        <span style="display: block; margin-top: 2px">
          The read command is queued through the command gateway
          (<code>{{ outcome?.command.command_id }}</code>) and will be acknowledged on the device's
          next heartbeat. This section is wired end-to-end and activates without UI changes once the
          device reports its configuration.
        </span>
      </WcCallout>
      <div v-else-if="commandError" class="error-text">{{ commandError }}</div>

      <WcCard
        v-if="values && descriptor"
        :title="descriptor.title"
        subtitle="Values reported by the device; saving queues a signed configuration write."
      >
        <SchemaForm
          ref="formRef"
          :descriptor="descriptor"
          :values="values"
          :disabled="saving"
          @save="save"
        />
      </WcCard>

      <WcCard
        v-else-if="values"
        title="Reported configuration"
        subtitle="Live values reported by the device."
      >
        <div class="table-wrap">
          <table class="table">
            <tbody>
              <tr v-for="(value, key) in values" :key="String(key)">
                <td style="width: 40%"><code>{{ key }}</code></td>
                <td>{{ typeof value === 'object' ? JSON.stringify(value) : String(value) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </WcCard>

      <WcCard v-else-if="hasDescriptor" :title="descriptor!.title" subtitle="Schema registered; waiting for device data.">
        <WcEmptyState
          title="No configuration reported yet"
          subtitle="The device has not reported values for this section. Use the read command below to poll it again."
        />
        <div class="form-actions">
          <button class="btn btn-outline" @click="read">
            <RefreshCw /> Read configuration
          </button>
        </div>
      </WcCard>

      <WcCard v-else title="Section configuration" subtitle="Delivered through the device configuration contract.">
        <WcEmptyState
          title="Awaiting the device configuration contract"
          subtitle="Settings become editable here as soon as the device reports its configuration schema."
        />
        <div class="form-actions">
          <button class="btn btn-outline" @click="read">
            <RefreshCw /> Read configuration
          </button>
        </div>
      </WcCard>

      <WcConfirmDialog
        v-model:open="leaveConfirmOpen"
        title="Discard unsaved changes?"
        description="This section has unsaved configuration changes. Leaving now discards them."
        confirm-label="Discard and leave"
        destructive
        @confirm="discardAndLeave"
      />
    </template>
  </div>
</template>