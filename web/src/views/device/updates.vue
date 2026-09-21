<script setup lang="ts">
// Updates — HQ operation catalog for device updates (WebConfig updates.js
// slot-management analog; rollout delivery runs through the command gateway).
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'
import type { Operation } from '@/lib/types'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

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
              :class="op.integration_status ? 'badge-warning' : 'badge-success'"
            >
              {{ op.integration_status ? 'awaiting contract' : 'available' }}
            </span>
          </div>
        </div>
      </template>
    </WcCard>

    <WcCallout kind="warning">
      Signed update artifacts are applied by the device configuration daemon. End-to-end rollout
      becomes available once the device configuration contract is connected; until then commands
      queue and are acknowledged on the device's next heartbeat.
    </WcCallout>
  </div>
</template>