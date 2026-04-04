<template>
  <div v-if="!events || events.length === 0" class="py-12 flex flex-col items-center justify-center border border-dashed border-white/5 rounded-xl bg-white/[0.01]">
    <div class="h-8 w-8 rounded-full border border-white/5 flex items-center justify-center mb-3">
      <div class="h-1 w-1 rounded-full bg-white/20 animate-pulse"></div>
    </div>
    <p class="text-[9px] font-bold uppercase tracking-[0.2em] text-white/20">等待事件信号...</p>
  </div>
  <div v-else class="relative space-y-8 pl-4 before:absolute before:left-0 before:top-2 before:h-[calc(100%-8px)] before:w-px before:bg-border/30">
    <div
      v-for="event in events"
      :key="event.id"
      class="group relative"
    >
      <!-- Timeline Dot -->
      <div class="absolute -left-[21px] top-1.5 h-3 w-3 rounded-full border-2 border-background shadow-sm" :class="getToneBgClass(event.event_status)"></div>

      <div class="flex flex-col gap-1 px-2">
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-foreground/80">{{ getEventLabel(event.event_type) }}</span>
            <span class="text-[10px] font-bold text-muted-foreground/30 px-1.5 py-0.5 rounded bg-muted/30 uppercase tracking-tighter">{{ event.event_phase }}</span>
          </div>
          <span class="text-[10px] font-medium tabular-nums text-muted-foreground/40">{{ event.occurred_at }}</span>
        </div>

        <p class="text-[11px] leading-relaxed text-muted-foreground/60 max-w-[90%]">{{ event.message || '捕获到处理事件。' }}</p>

        <!-- Payload Preview -->
        <div v-if="hasPayload(event.payload)" class="mt-4 overflow-hidden rounded-lg border border-border/10 bg-muted/10 opacity-60 group-hover:opacity-100 transition-opacity">
          <div class="flex items-center justify-between px-3 py-1.5 border-b border-border/10 bg-muted/20">
            <span class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">数据负载</span>
          </div>
          <pre class="overflow-x-auto p-3 text-[10px] font-mono leading-relaxed text-muted-foreground/80">{{ formatPayload(event.payload) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SyncRunEvent } from '@/composables/useSyncHistory'

defineProps<{
  events: SyncRunEvent[]
}>()

const getToneBgClass = (status: string | null) => {
  switch (status) {
    case 'success': return 'bg-emerald-400'
    case 'failed': return 'bg-rose-500'
    case 'running': return 'bg-blue-500'
    default: return 'bg-slate-300'
  }
}

const getEventLabel = (eventType: string) => {
  const map: Record<string, string> = {
    'stale_queued_recovered': '队列恢复',
    'stale_running_recovered': '运行恢复',
    'subscription_sync_started': '同步开始',
    'subscription_sync_finished': '同步完成',
    'subscription_sync_failed': '同步失败',
  }
  return map[eventType] || eventType.replace(/_/g, ' ').toUpperCase()
}

const hasPayload = (payload: any) => {
  if (!payload) return false
  return Object.keys(payload).length > 0
}

const formatPayload = (payload: Record<string, unknown>) => {
  try {
    return JSON.stringify(payload || {}, null, 2)
  } catch (_) {
    return '{}'
  }
}
</script>
