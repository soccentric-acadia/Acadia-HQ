<script setup lang="ts">
// WebConfig card port: header (title + subtitle, optional actions) + body +
// optional footer slot. Styles come from wc.css (.card, .card-header, ...).
defineProps<{ title?: string; subtitle?: string }>()
</script>

<template>
  <div class="card">
    <div v-if="title || $slots.actions" class="card-header">
      <div>
        <h3>{{ title }}</h3>
        <div v-if="subtitle" class="card-header-sub">{{ subtitle }}</div>
      </div>
      <div class="row">
        <slot name="actions" />
      </div>
    </div>
    <div class="card-body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>