<script setup lang="ts">
// Power — reboot/shutdown (WebConfig power.js). HQ does not expose power
// commands yet, so the section states precisely what is pending.
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
</script>

<template>
  <div class="page-surface">
    <WcCard title="Power controls" subtitle="Restart or power off the device.">
      <WcEmptyState
        title="Power commands are not exposed by HQ yet"
        subtitle="Reboot and shutdown run on-device in WebConfig today."
      />
    </WcCard>
    <WcCallout kind="info">
      Power operations require a new HQ command kind delivered through the agent gateway; the UI is
      ready and the command channel will light this section up without further changes.
    </WcCallout>
  </div>
</template>