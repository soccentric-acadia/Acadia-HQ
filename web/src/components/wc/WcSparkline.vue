<script setup lang="ts">
// WebConfig sparkline port: rolling history polyline, no dependencies.
const props = withDefaults(defineProps<{ points?: number[]; height?: number }>(), {
  points: () => [],
  height: 42,
})

const width = 240

function path(points: number[]): string {
  if (points.length < 2) return ''
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  return points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * width
      const y = props.height - ((v - min) / span) * (props.height - 4) - 2
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" :style="{ height: `${height}px` }" class="w-full">
    <path :d="path(points)" fill="none" stroke="var(--primary)" stroke-width="1.6" />
  </svg>
</template>