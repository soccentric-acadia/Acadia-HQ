<script setup lang="ts">
// Remote Logs (admin) — device journal retrieval through HQ.
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
</script>

<template>
  <div class="page-surface">
    <WcCard title="Remote Logs" subtitle="Retrieve device journals through HQ.">
      <WcEmptyState
        title="Awaiting the device configuration contract"
        subtitle="Journal retrieval is delivered as a configuration command."
      />
    </WcCard>
    <WcCallout kind="info">
      The command channel is wired (`configuration.read`); this section activates when the device
      contract reports journal data.
    </WcCallout>
  </div>
</template>