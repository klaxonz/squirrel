<template>
  <Teleport to="body">
    <transition name="sync-drawer">
      <div
        v-if="open && run"
        class="fixed inset-0 z-50 flex justify-end bg-overlay-dark-50"
        @click.self="emit('close')"
      >
        <div class="flex h-full w-full max-w-3xl flex-col border-l border-border-primary bg-bg-primary shadow-2xl">
          <div class="px-6 py-5 border-b border-border-primary flex items-start justify-between gap-4">
            <div class="min-w-0">
              <h2 class="text-lg font-semibold leading-7 text-text-primary break-words">{{ run.subscription_name }}</h2>
              <div class="flex flex-wrap items-center gap-2 mt-2">
                <StatusBadge size="xs" :show-dot="false" :variant="getVariant(run.status)" :label="run.status" class="border-0" />
                <span class="px-2 py-0.5 rounded-full text-2xs bg-bg-secondary text-text-tertiary border border-border-primary">
                  {{ run.sync_mode }}
                </span>
                <span class="text-2xs text-text-muted">{{ run.site || 'unknown' }}</span>
                <span class="text-2xs text-text-muted">run {{ run.run_id }}</span>
              </div>
            </div>
            <button
              type="button"
              class="h-9 w-9 rounded-full bg-bg-secondary text-text-secondary hover:bg-bg-hover transition-colors"
              @click="emit('close')"
            >
              ✕
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            <div class="grid grid-cols-2 gap-3">
              <Card class="p-4">
                <p class="text-2xs text-text-tertiary">开始时间</p>
                <p class="text-sm text-text-primary mt-2">{{ run.started_at || '—' }}</p>
              </Card>
              <Card class="p-4">
                <p class="text-2xs text-text-tertiary">耗时</p>
                <p class="text-sm text-text-primary mt-2">{{ formatDurationMs(run.duration_ms) }}</p>
              </Card>
              <Card class="p-4">
                <p class="text-2xs text-text-tertiary">{{ getVideoSummaryLabel(run.sync_mode) }}</p>
                <p class="text-sm text-text-primary mt-2">{{ run.videos_found }} / {{ run.videos_enqueued }} / {{ run.videos_extracted }}</p>
              </Card>
              <Card class="p-4">
                <p class="text-2xs text-text-tertiary">本次扫描视频数</p>
                <p class="text-sm text-text-primary mt-2">{{ formatSourceVideoCount(run.source_video_count) }}</p>
              </Card>
              <Card class="p-4">
                <p class="text-2xs text-text-tertiary">失败次数</p>
                <p class="text-sm text-text-primary mt-2">{{ run.failure_count }}</p>
              </Card>
            </div>

            <Card class="p-4">
              <div class="space-y-2 text-xs">
                <div class="flex items-center justify-between gap-4">
                  <span class="text-text-tertiary">request_id</span>
                  <span class="text-text-primary">{{ run.request_id || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4">
                  <span class="text-text-tertiary">trace_id</span>
                  <span class="text-text-primary">{{ run.trace_id || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4">
                  <span class="text-text-tertiary">当前阶段</span>
                  <span class="text-text-primary">{{ run.current_phase || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4">
                  <span class="text-text-tertiary">最后事件</span>
                  <span class="text-text-primary">{{ run.last_event_at }}</span>
                </div>
              </div>
            </Card>

            <Card class="p-4">
              <h3 class="text-sm font-medium text-text-primary mb-3">事件时间线</h3>
              <div v-if="detailLoading" class="text-xs text-text-muted">加载事件中...</div>
              <div v-else-if="detailError" class="text-xs text-color-error">{{ detailError }}</div>
              <SyncEventTimeline v-else :events="events" />
            </Card>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { Card, StatusBadge } from '@/components/common'
import type { SyncRunEvent, SyncRunItem } from '@/composables/useSyncHistory'
import SyncEventTimeline from '@/components/sync-center/SyncEventTimeline.vue'
import { formatDurationMs } from '@/utils/dateFormat'

defineProps<{
  detailError: string
  detailLoading: boolean
  events: SyncRunEvent[]
  open: boolean
  run: SyncRunItem | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const getVariant = (status: string) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'error'
    case 'deferred':
      return 'warning'
    case 'running':
    case 'queued':
      return 'info'
    default:
      return 'default'
  }
}

const getVideoSummaryLabel = (syncMode: string) => {
  return syncMode === 'incremental' ? '新增发现 / 入队 / 提取' : '发现 / 入队 / 提取'
}

const formatSourceVideoCount = (value?: number | null) => {
  return value == null ? '—' : String(value)
}
</script>

<style scoped>
.sync-drawer-enter-active,
.sync-drawer-leave-active {
  transition: opacity 180ms ease;
}

.sync-drawer-enter-from,
.sync-drawer-leave-to {
  opacity: 0;
}
</style>
