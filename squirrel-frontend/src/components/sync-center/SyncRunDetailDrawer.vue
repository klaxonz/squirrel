<template>
  <Sheet :open="open && !!run" @update:open="handleSheetToggle">
    <SheetContent side="right" class="w-full max-w-3xl bg-background p-0">
      <div v-if="run" class="flex h-full flex-col">
        <div class="border-b border-border px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div class="flex min-w-0 items-start gap-3">
              <router-link :to="getSubscriptionLink(run.subscription_id)" class="shrink-0">
                <img
                  :src="getAvatarSrc(run.subscription_avatar, `run-drawer-${run.run_id}`)"
                  :alt="run.subscription_name"
                  class="h-12 w-12 rounded-full object-cover bg-card ring-1 ring-border"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, `run-drawer-${run?.run_id || 'unknown'}`)"
                >
              </router-link>

              <div class="min-w-0">
                <router-link
                  :to="getSubscriptionLink(run.subscription_id)"
                  class="text-lg font-semibold leading-7 text-foreground break-words hover:text-primary"
                >
                  {{ run.subscription_name }}
                </router-link>

                <div class="mt-2 flex flex-wrap items-center gap-2">
                  <Badge :variant="getBadgeVariant(run.status)" class="rounded-md px-2 py-0.5">{{ getStatusLabel(run.status) }}</Badge>
                  <Badge variant="outline" class="rounded-md px-2 py-0.5">{{ getModeLabel(run.sync_mode) }}</Badge>
                  <span class="text-2xs text-muted-foreground">{{ run.site || 'unknown' }}</span>
                  <span class="text-2xs text-muted-foreground">run {{ run.run_id }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <Button as-child variant="secondary" size="sm">
                <router-link :to="getSubscriptionLink(run.subscription_id)">打开频道</router-link>
              </Button>
            </div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <div class="grid grid-cols-2 gap-3">
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground">开始时间</p>
                <p class="mt-2 text-sm text-foreground">{{ run.started_at || '—' }}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground">耗时</p>
                <p class="mt-2 text-sm text-foreground">{{ formatDurationMs(run.duration_ms) }}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground">{{ getVideoSummaryLabel(run.sync_mode) }}</p>
                <p class="mt-2 text-sm text-foreground">{{ run.videos_found }} / {{ run.videos_enqueued }} / {{ run.videos_extracted }}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground">本次扫描视频数</p>
                <p class="mt-2 text-sm text-foreground">{{ formatSourceVideoCount(run.source_video_count) }}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground">失败次数</p>
                <p class="mt-2 text-sm text-foreground">{{ run.failure_count }}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent class="p-4">
              <div class="space-y-2 text-xs">
                <div class="flex items-center justify-between gap-4">
                  <span class="text-muted-foreground">request_id</span>
                  <span class="text-foreground">{{ run.request_id || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4">
                  <span class="text-muted-foreground">trace_id</span>
                  <span class="text-foreground">{{ run.trace_id || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4">
                  <span class="text-muted-foreground">当前阶段</span>
                  <span class="text-foreground">{{ run.current_phase || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4">
                  <span class="text-muted-foreground">最后事件</span>
                  <span class="text-foreground">{{ run.last_event_at }}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <h3 class="mb-3 text-sm font-medium text-foreground">事件时间线</h3>
              <div v-if="detailLoading" class="text-xs text-muted-foreground">加载事件中...</div>
              <div v-else-if="detailError" class="text-xs text-destructive">{{ detailError }}</div>
              <SyncEventTimeline v-else :events="events" />
            </CardContent>
          </Card>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
import type { SyncRunEvent, SyncRunItem } from '@/composables/useSyncHistory'
import SyncEventTimeline from '@/components/sync-center/SyncEventTimeline.vue'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDurationMs } from '@/utils/dateFormat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const props = defineProps<{
  detailError: string
  detailLoading: boolean
  events: SyncRunEvent[]
  open: boolean
  run: SyncRunItem | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()

const getSubscriptionLink = (subscriptionId: number) => `/subscription/${subscriptionId}/all`

const handleSheetToggle = (value: boolean) => {
  if (!value) {
    emit('close')
  }
}

const getBadgeVariant = (status: string) => {
  switch (status) {
    case 'success':
      return 'secondary'
    case 'failed':
      return 'destructive'
    case 'deferred':
    case 'timeout':
      return 'outline'
    case 'running':
    case 'queued':
      return 'default'
    default:
      return 'outline'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'created':
      return '已创建'
    case 'queued':
      return '排队中'
    case 'running':
      return '运行中'
    case 'success':
      return '成功'
    case 'failed':
      return '失败'
    case 'deferred':
      return '已延后'
    case 'timeout':
      return '超时'
    default:
      return status || '未知'
  }
}

const getModeLabel = (mode: string) => {
  return mode === 'incremental' ? '增量' : mode === 'full' ? '全量' : mode || '未知'
}

const getVideoSummaryLabel = (syncMode: string) => {
  return syncMode === 'incremental' ? '新增发现 / 入队 / 提取' : '发现 / 入队 / 提取'
}

const formatSourceVideoCount = (value?: number | null) => {
  return value == null ? '—' : String(value)
}
</script>

