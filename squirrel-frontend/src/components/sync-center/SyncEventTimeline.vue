<template>
  <div class="space-y-3">
    <div
      v-for="event in events"
      :key="event.id"
      class="rounded-xl bg-background border border-border p-3"
    >
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <Badge :variant="getVariant(event.event_status)">
            {{ getEventLabel(event.event_type) }}
          </Badge>
          <span class="text-2xs text-muted-foreground/70 truncate">{{ event.event_phase || 'phase:unknown' }}</span>
        </div>
        <span class="text-2xs text-muted-foreground">{{ event.occurred_at }}</span>
      </div>
      <div class="text-xs text-muted-foreground mt-2">{{ event.message || '无附加消息' }}</div>
      <pre class="mt-3 whitespace-pre-wrap break-all text-2xs text-muted-foreground bg-card rounded-lg p-3">{{ formatPayload(event.payload) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SyncRunEvent } from '@/composables/useSyncHistory'
import { Badge } from '@/components/ui/badge'

defineProps<{
  events: SyncRunEvent[]
}>()

const getVariant = (status: string | null) => {
  switch (status) {
    case 'success':
      return 'secondary'
    case 'failed':
      return 'destructive'
    case 'deferred':
      return 'outline'
    case 'running':
      return 'default'
    default:
      return 'outline'
  }
}

const getEventLabel = (eventType: string) => {
  switch (eventType) {
    case 'stale_queued_recovered':
      return '恢复 queued'
    case 'stale_running_recovered':
      return '恢复 running'
    case 'manual_reconcile_triggered':
      return '手动对账'
    default:
      return eventType
  }
}

const formatPayload = (payload: Record<string, unknown>) => {
  try {
    return JSON.stringify(payload || {}, null, 2)
  } catch (_) {
    return '{}'
  }
}
</script>
