<script setup lang="ts">
// Section host — resolves the active device section from the registry and
// lazy-loads its component. Configuration-backed sections additionally get
// the pending-contract callout injected by their own components.
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { SECTION_HEADERS, sectionMeta } from '@/lib/deviceSections'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const route = useRoute()

const sectionId = computed(() => String(route.params.section ?? 'overview'))
const meta = computed(() => sectionMeta(sectionId.value))
const header = computed(() => SECTION_HEADERS[sectionId.value])

const sectionComponent = computed(() => {
  if (!meta.value) return null
  return defineAsyncComponent({
    loader: meta.value.loader,
    loadingComponent: WcSkeleton,
    delay: 0,
  })
})
</script>

<template>
  <div>
    <div v-if="header" class="page-header" style="margin-bottom: var(--space-5)">
      <h1>{{ header.title }}</h1>
      <p>{{ header.description }}</p>
    </div>
    <WcEmptyState
      v-if="!meta"
      title="Unknown section"
      :subtitle="`No device section matches '${sectionId}'.`"
    />
    <component :is="sectionComponent" v-else-if="sectionComponent" :device-id="String(route.params.id)" />
  </div>
</template>