<template>
  <section class="flex flex-wrap items-center gap-6 px-1">
    <div
      v-for="item in displaySignals"
      :key="item.key"
      class="flex items-center gap-2.5 cursor-pointer group"
      @click="emit('select', item.key)"
    >
      <div :class="[getToneBgClass(item.tone), 'flex h-8 w-8 items-center justify-center rounded-lg transition-colors group-hover:bg-opacity-80']">
        <component :is="item.icon" :class="[getToneTextClass(item.tone), 'h-4 w-4']" />
      </div>
      <div class="flex flex-col">
        <span class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">{{ item.label }}</span>
        <span class="text-sm font-semibold tabular-nums text-foreground">{{ item.value }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AlertCircle, Activity, CheckCircle2, Clock, Layers, PlayCircle } from 'lucide-vue-next'

type SignalTone = 'neutral' | 'info' | 'warning' | 'error' | 'success'

export interface SyncSignalItem {
  key: string
  label: string
  value: string | number
  tone: SignalTone
  delta?: string
}

const props = defineProps<{
  current: SyncSignalItem[]
  recent: SyncSignalItem[]
}>()

const emit = defineEmits<{
  (e: 'select', key: string): void
}>()

const displaySignals = computed(() => {
  const all = [...props.current, ...props.recent]
  const map: Record<string, { label: string; icon: any }> = {
    'failed': { label: 'Errors', icon: AlertCircle },
    'running': { label: 'Processing', icon: Activity },
    'queued': { label: 'In Queue', icon: Clock },
    'success-rate': { label: 'Success Rate', icon: CheckCircle2 },
    'pending-videos': { label: 'Pending', icon: Layers },
    'extracted': { label: 'Extracted', icon: PlayCircle },
  }

  return all
    .filter(item => map[item.key])
    .map(item => ({
      ...item,
      label: map[item.key].label,
      icon: map[item.key].icon,
    }))
    .sort((a, b) => {
      const order = ['failed', 'running', 'queued', 'pending-videos', 'success-rate', 'extracted']
      return order.indexOf(a.key) - order.indexOf(b.key)
    })
})

const getToneBgClass = (tone: SignalTone) => {
  switch (tone) {
    case 'success': return 'bg-emerald-500/10'
    case 'error': return 'bg-rose-500/10'
    case 'warning': return 'bg-amber-500/10'
    case 'info': return 'bg-blue-500/10'
    default: return 'bg-slate-500/10'
  }
}

const getToneTextClass = (tone: SignalTone) => {
  switch (tone) {
    case 'success': return 'text-emerald-600'
    case 'error': return 'text-rose-600'
    case 'warning': return 'text-amber-600'
    case 'info': return 'text-blue-600'
    default: return 'text-slate-600'
  }
}
</script>