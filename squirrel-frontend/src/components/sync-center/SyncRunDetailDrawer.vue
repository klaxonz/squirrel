<template>
  <Sheet :open="open && !!run" @update:open="handleSheetToggle">
    <SheetContent side="right" class="w-full max-w-2xl border-l border-border/40 bg-background p-0 shadow-2xl">
      <div v-if="run" class="flex h-full flex-col overflow-hidden">
        <!-- Drawer Header -->
        <div class="px-4 sm:px-8 pt-8 sm:pt-10 pb-4 sm:pb-6">
          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 sm:gap-6">
            <div class="flex min-w-0 items-center gap-3 sm:gap-4">
              <img
                :src="getAvatarSrc(run.subscription_avatar, `run-drawer-${run.run_id}`)"
                :alt="run.subscription_name"
                class="sync-run-detail-drawer__avatar h-10 w-10 object-cover sm:h-14 sm:w-14"
                referrerpolicy="no-referrer"
                @error="(e) => handleAvatarError(e, `run-drawer-${run?.run_id || 'unknown'}`)"
              >
              <div class="min-w-0 space-y-0.5 sm:space-y-1">
                <h2 class="text-lg sm:text-xl font-bold tracking-tight text-foreground/90 truncate max-w-[14rem] sm:max-w-[18rem]">
                  {{ run.subscription_name }}
                </h2>
                <div class="flex items-center gap-2">
                  <div :class="[getStatusToneClass(run.status), 'h-1.5 w-1.5 sm:h-2 sm:w-2 rounded-full']"></div>
                  <span class="inline-flex items-center gap-2 text-[10px] sm:text-xs font-bold uppercase tracking-wider text-muted-foreground/60">
                    <span>{{ getStatusLabel(run.status) }}</span>
                  </span>
                </div>
              </div>
            </div>
            <Button variant="outline" size="sm" class="h-8 sm:self-start self-end rounded-lg text-[10px] sm:text-[11px] font-bold uppercase tracking-wider" as-child>
              <router-link :to="getSubscriptionLink(run.subscription_id)">去频道</router-link>
            </Button>
          </div>
        </div>

        <!-- Scrollable Content -->
        <div class="flex-1 overflow-y-auto px-4 sm:px-8 py-4 space-y-8 sm:space-y-10 selection:bg-primary/10">
          <!-- Quick Stats -->
          <div class="grid grid-cols-2 gap-3 sm:gap-4">
            <div class="rounded-xl border border-border/40 bg-muted/10 p-3 sm:p-4 transition-colors hover:bg-muted/20">
              <p class="text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/40">持续时间</p>
              <p class="mt-1 sm:mt-2 text-base sm:text-lg font-bold tabular-nums text-foreground/80">{{ formatDurationMs(run.duration_ms) }}</p>
            </div>
            <div class="rounded-xl border border-border/40 bg-muted/10 p-3 sm:p-4 transition-colors hover:bg-muted/20">
              <p class="text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/40">已提取</p>
              <p class="mt-1 sm:mt-2 text-base sm:text-lg font-bold tabular-nums text-foreground/80">{{ run.videos_extracted }} 项</p>
            </div>
          </div>

          <!-- Technical Specs -->
          <section class="space-y-4">
            <div class="flex items-center gap-2 px-1">
              <div class="h-px flex-1 bg-border/40"></div>
              <span class="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/30 whitespace-nowrap">技术参数</span>
              <div class="h-px flex-1 bg-border/40"></div>
            </div>
            <div class="grid grid-cols-1 gap-y-3 px-1">
              <div class="flex items-center justify-between py-1 border-b border-border/10">
                <span class="text-[11px] font-semibold text-muted-foreground/50">运行编号</span>
                <span class="text-[11px] font-mono font-medium text-foreground/70">{{ run.run_id }}</span>
              </div>
              <div class="flex items-center justify-between py-1 border-b border-border/10">
                <span class="text-[11px] font-semibold text-muted-foreground/50">同步模式</span>
                <span class="text-[11px] font-bold uppercase tracking-wider text-foreground/70">{{ getSyncModeLabel(run.sync_mode) }}</span>
              </div>
              <div class="flex items-center justify-between py-1 border-b border-border/10">
                <span class="text-[11px] font-semibold text-muted-foreground/50">时间戳</span>
                <span class="text-[11px] font-medium text-foreground/70 tabular-nums">{{ run.started_at }}</span>
              </div>
              <div class="flex items-center justify-between py-1 border-b border-border/10">
                <span class="text-[11px] font-semibold text-muted-foreground/50">追踪编号</span>
                <span class="text-[11px] font-mono text-muted-foreground/60">{{ run.trace_id || '—' }}</span>
              </div>
            </div>
          </section>

          <!-- Timeline -->
          <section class="space-y-6 pb-10">
             <div class="flex items-center justify-between px-1">
               <h3 class="text-xs font-bold uppercase tracking-[0.15em] text-foreground/80">事件时间轴</h3>
               <span v-if="detailLoading" class="text-[10px] font-medium text-blue-500 animate-pulse">流式传输中...</span>
             </div>
             <div v-if="detailError" class="rounded-lg bg-rose-500/10 p-3 text-[11px] text-rose-600 font-medium">
               {{ detailError }}
             </div>
             <SyncEventTimeline v-else :events="events" />
          </section>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SyncRunEvent, SyncRunItem } from '@/composables/useSyncHistory'
import SyncEventTimeline from '@/components/sync-center/SyncEventTimeline.vue'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDurationMs } from '@/utils/dateFormat'
import { getSyncModeLabel } from '@/utils/syncMode'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const props = withDefaults(defineProps<{
  detailError: string
  detailLoading: boolean
  events: SyncRunEvent[]
  open: boolean
  run: SyncRunItem | null
  siteOptions?: Array<{ value: string; label: string; iconUrl?: string | null }>
}>(), {
  siteOptions: () => [],
})

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

const getStatusToneClass = (status: string) => {
  switch (status) {
    case 'success': return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]'
    case 'failed': return 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]'
    case 'running': return 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.4)]'
    case 'queued': return 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.4)]'
    default: return 'bg-slate-300'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'running': return '运行中'
    case 'queued': return '排队中'
    case 'deferred': return '已延后'
    default: return status || '未知'
  }
}
</script>

<style scoped>
.sync-run-detail-drawer__avatar {
  border-radius: 9999px;
}
</style>
