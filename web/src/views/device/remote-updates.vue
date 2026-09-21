<script setup lang="ts">
// Remote Updates (admin) — stage and apply device updates through HQ.
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
</script>

<template>
  <div class="page-surface">
    <WcCard title="Remote Updates" subtitle="Stage and apply signed device updates through HQ.">
      <WcEmptyState
        title="Awaiting the device configuration contract"
        subtitle="Update staging is delivered as a configuration command."
      />
    </WcCard>
    <WcCallout kind="info">
      The command channel is wired (`apply_update`); this section activates when the device
      contract accepts signed artifacts end-to-end.
    </WcCallout>
  </div>
</template>