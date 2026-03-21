<template>
  <div class="space-y-3">
    <div
      v-for="event in events"
      :key="event.id"
      class="rounded-xl bg-bg-primary border border-border-primary p-3"
    >
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <StatusBadge
            size="xs"
            :show-dot="false"
            :variant="getVariant(event.event_status)"
            :label="getEventLabel(event.event_type)"
            class="border-0"
          />
          <span class="text-2xs text-text-tertiary truncate">{{ event.event_phase || 'phase:unknown' }}</span>
        </div>
        <span class="text-2xs text-text-muted">{{ event.occurred_at }}</span>
      </div>
      <div class="text-xs text-text-secondary mt-2">{{ event.message || '无附加消息' }}</div>
      <pre class="mt-3 whitespace-pre-wrap break-all text-2xs text-text-muted bg-bg-secondary rounded-lg p-3">{{ formatPayload(event.payload) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { StatusBadge } from '@/components/common'
import type { SyncRunEvent } from '@/composables/useSyncHistory'

defineProps<{
  events: SyncRunEvent[]
}>()

const getVariant = (status: string | null) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'error'
    case 'deferred':
      return 'warning'
    case 'running':
      return 'info'
    default:
      return 'default'
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
