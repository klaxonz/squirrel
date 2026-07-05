<template>
  <div
    class="inline-flex items-center gap-1 px-1.5 py-px rounded border transition-colors duration-200"
    :style="tagStyles"
  >
    <div class="h-2.5 w-0.5 rounded-sm" :style="{ backgroundColor: siteColor }" />
    <span class="text-xs font-semibold leading-none">
      {{ site }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  site?: string | null
}>()

const siteConfig: Record<string, { color: string, bg: string, border: string }> = {
  'bilibili': { color: '#fb7299', bg: 'rgba(251, 114, 153, 0.1)', border: 'rgba(251, 114, 153, 0.2)' },
  'youtube': { color: '#ff0000', bg: 'rgba(255, 0, 0, 0.1)', border: 'rgba(255, 0, 0, 0.2)' },
  'twitter': { color: '#1da1f2', bg: 'rgba(29, 161, 242, 0.1)', border: 'rgba(29, 161, 242, 0.2)' },
  'instagram': { color: '#e1306c', bg: 'rgba(225, 48, 108, 0.1)', border: 'rgba(225, 48, 108, 0.2)' },
  'tiktok': { color: '#00f2ea', bg: 'rgba(0, 242, 234, 0.1)', border: 'rgba(0, 242, 234, 0.2)' },
  'pornhub': { color: '#ffa500', bg: 'rgba(255, 165, 0, 0.1)', border: 'rgba(255, 165, 0, 0.2)' },
  'youporn': { color: '#ff0000', bg: 'rgba(255, 0, 0, 0.1)', border: 'rgba(255, 0, 0, 0.2)' },
  'jable': { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.2)' },
}

const config = computed(() => {
  const s = props.site?.toLowerCase()
  return (s && siteConfig[s]) || { color: 'currentColor', bg: 'hsl(var(--accent) / 0.5)', border: 'hsl(var(--border) / 0.5)' }
})

const siteColor = computed(() => config.value.color)
const tagStyles = computed(() => ({
  backgroundColor: config.value.bg,
  borderColor: config.value.border,
  color: config.value.color
}))
</script>
