<template>
  <section class="grid min-h-0 grid-cols-1 gap-3 xl:grid-cols-[17rem_minmax(0,1.25fr)_22rem]">
    <aside class="overflow-hidden rounded-2xl border border-border-primary bg-bg-secondary">
      <div class="flex items-center justify-between border-b border-border-primary px-3 py-2.5">
        <div>
          <div class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">{{ workspaceLabel }}</div>
          <div class="mt-1 text-2xs text-text-muted">{{ workspaceMeta }}</div>
        </div>
        <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
          {{ objectRows.length }}
        </span>
      </div>

      <div v-if="objectRows.length" class="divide-y divide-border-primary">
        <button
          v-for="row in objectRows"
          :key="row.id"
          type="button"
          class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-bg-hover"
          :class="row.active ? 'bg-bg-hover' : ''"
          @click="handleObjectRowClick(row)"
        >
          <div class="min-w-0">
            <div class="truncate text-xs font-medium text-text-primary">{{ row.title }}</div>
            <div class="mt-0.5 truncate text-2xs text-text-tertiary">{{ row.meta }}</div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <span class="h-2 w-2 rounded-full" :class="getDotClass(row.tone)"></span>
            <span class="text-xs font-semibold" :class="getValueClass(row.tone)">{{ row.value }}</span>
          </div>
        </button>
      </div>
      <div v-else class="px-3 py-6 text-center text-2xs text-text-muted">
        当前没有可分析对象
      </div>
    </aside>

    <div class="min-h-0 space-y-3">
      <SyncTrendCharts
        v-if="showTrendPanel"
        embedded
        :error="trendError"
        :filters="trendFilters"
        :loading="trendLoading"
        :range="trendRange"
        :series="trendSeries"
        :site-breakdown="siteBreakdown"
        @set-filter="emit('change-trend-filter', $event)"
        @set-range="emit('change-trend-range', $event)"
      />

      <SyncRunHistoryPanel
        embedded
        :error="runsError"
        :filters="runFilters"
        :loading="runsLoading"
        :page="runPage"
        :page-size="runPageSize"
        :runs="runs"
        :selected-run-id="selectedRunId"
        :total="runTotal"
        @change-page="emit('change-history-page', $event)"
        @open-run="emit('open-run', $event)"
        @set-filter="emit('change-history-filter', $event)"
      />
    </div>

    <aside class="min-h-0 space-y-3">
      <div class="overflow-hidden rounded-2xl border border-border-primary bg-bg-secondary">
        <div class="border-b border-border-primary px-3 py-2.5">
          <div class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">分析摘要</div>
        </div>

        <div class="grid grid-cols-2 gap-px bg-border-primary">
          <div
            v-for="metric in summaryMetrics"
            :key="metric.label"
            class="bg-bg-primary px-3 py-2.5"
          >
            <div class="text-2xs text-text-tertiary">{{ metric.label }}</div>
            <div class="mt-1 text-xs font-semibold text-text-primary">{{ metric.value }}</div>
          </div>
        </div>

        <div v-if="selectedRun" class="border-t border-border-primary px-3 py-3">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate text-xs font-medium text-text-primary">{{ selectedRun.subscription_name }}</div>
              <div class="mt-0.5 truncate text-2xs text-text-tertiary">
                run {{ selectedRun.run_id }} · {{ selectedRun.site || 'unknown' }}
              </div>
            </div>
            <Button
              size="xs"
              shape="pill"
              variant="secondary"
              @click="emit('open-run', selectedRun.run_id)"
            >
              事件
            </Button>
          </div>
          <div class="mt-2 text-2xs text-text-muted">
            {{ selectedRun.error_message || `${selectedRun.duration_ms} ms · ${formatRunSummary(selectedRun)}` }}
          </div>
        </div>

        <div v-else-if="selectedItem" class="border-t border-border-primary px-3 py-3">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate text-xs font-medium text-text-primary">{{ selectedItem.subscription_name }}</div>
              <div class="mt-0.5 truncate text-2xs text-text-tertiary">
                {{ selectedItem.site || 'unknown' }} · {{ selectedItem.sync_mode }}
              </div>
            </div>
            <Button
              size="xs"
              shape="pill"
              variant="secondary"
              @click="emit('open-item', selectedItem)"
            >
              订阅
            </Button>
          </div>
          <div class="mt-2 text-2xs text-text-muted">
            {{ selectedItem.last_error_summary || `${selectedItem.pending_video_count || 0} 个待处理` }}
          </div>
        </div>
      </div>

      <SyncItemsPanel
        embedded
        :active-status="itemStatus"
        :items="items"
        :loading="itemsLoading"
        :page="itemPage"
        :page-size="itemPageSize"
        :retrying-id="retryingId"
        :selected-id="selectedSubscriptionId"
        :total="itemTotal"
        @change-page="emit('change-item-page', $event)"
        @change-status="emit('change-item-status', $event)"
        @open-item="emit('open-item', $event)"
        @retry-item="emit('retry-item', $event)"
      />
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/common'
import SyncItemsPanel from '@/components/sync-center/SyncItemsPanel.vue'
import SyncRunHistoryPanel from '@/components/sync-center/SyncRunHistoryPanel.vue'
import SyncTrendCharts from '@/components/sync-center/SyncTrendCharts.vue'
import type { SyncCenterItem, SyncCenterStatusFilter } from '@/composables/useSyncCenter'
import type { SyncFocusKind } from '@/composables/useSyncCenterWorkbench'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import type { SyncTrendPoint, SyncTrendSiteBreakdown } from '@/composables/useSyncTrends'

interface RecoverySummary {
  last_reconcile_at: string
  total_recovered: number
  by_type: Record<string, number>
  window_hours: number
}

type AnalysisTone = 'neutral' | 'info' | 'warning' | 'error' | 'success'

interface ObjectRow {
  id: string
  title: string
  meta: string
  value: string | number
  tone: AnalysisTone
  active?: boolean
}

const props = defineProps<{
  focus: SyncFocusKind
  site: string
  runs: SyncRunItem[]
  runsError: string
  runsLoading: boolean
  runFilters: Record<string, string>
  runPage: number
  runPageSize: number
  runTotal: number
  trendError: string
  trendFilters: Record<string, string>
  trendLoading: boolean
  trendRange: string
  trendSeries: SyncTrendPoint[]
  siteBreakdown: SyncTrendSiteBreakdown[]
  items: SyncCenterItem[]
  itemsLoading: boolean
  itemPage: number
  itemPageSize: number
  itemStatus: SyncCenterStatusFilter
  itemTotal: number
  retryingId: number | null
  selectedItem: SyncCenterItem | null
  selectedRun: SyncRunItem | null
  selectedRunId: string
  selectedSubscriptionId: number | null
  recoverySummary: RecoverySummary
}>()

const emit = defineEmits<{
  (e: 'change-history-filter', payload: { key: string; value: string }): void
  (e: 'change-history-page', page: number): void
  (e: 'change-item-page', page: number): void
  (e: 'change-item-status', status: SyncCenterStatusFilter): void
  (e: 'change-trend-filter', payload: { key: string; value: string }): void
  (e: 'change-trend-range', value: string): void
  (e: 'focus-site', site: string): void
  (e: 'open-item', item: SyncCenterItem): void
  (e: 'open-recovery'): void
  (e: 'open-run', runId: string): void
  (e: 'retry-item', item: SyncCenterItem): void
}>()

const failedRuns = computed(() => props.runs.filter((run) => run.status === 'failed'))
const slowRuns = computed(() => [...props.runs].sort((left, right) => right.duration_ms - left.duration_ms))
const selectedSiteBreakdown = computed(() => {
  if (!props.site) {
    return null
  }
  return props.siteBreakdown.find((item) => item.site === props.site) || null
})
const highestP95 = computed(() => {
  if (!props.trendSeries.length) {
    return 0
  }
  return Math.max(...props.trendSeries.map((item) => item.p95_duration_ms || 0))
})

const workspaceLabel = computed(() => {
  switch (props.focus) {
    case 'site':
      return '站点剖面'
    case 'failed-runs':
      return '失败批次'
    case 'slow-runs':
      return '高延迟批次'
    case 'recovery':
      return '恢复分析'
    default:
      return '分析工作区'
  }
})

const workspaceMeta = computed(() => {
  switch (props.focus) {
    case 'site':
      return props.site ? `当前站点 ${props.site}` : '选择一个站点查看剖面'
    case 'failed-runs':
      return '聚焦最近失败运行及其影响面'
    case 'slow-runs':
      return '聚焦耗时偏高的运行批次'
    case 'recovery':
      return `最近 ${props.recoverySummary.window_hours}h 的恢复动作`
    default:
      return '从左侧对象流进入分析'
  }
})

const objectRows = computed<ObjectRow[]>(() => {
  switch (props.focus) {
    case 'site':
      return props.siteBreakdown.slice(0, 10).map((item) => ({
        id: item.site,
        title: item.site,
        meta: `运行 ${item.runs_total} · 成功 ${item.runs_success}`,
        value: item.runs_failed,
        tone: item.runs_failed > 0 ? 'error' : 'success',
        active: item.site === props.site,
      }))
    case 'failed-runs':
      return failedRuns.value.slice(0, 10).map((run) => ({
        id: run.run_id,
        title: run.subscription_name,
        meta: `${run.site || 'unknown'} · ${run.last_event_at || run.finished_at || '—'}`,
        value: `${run.duration_ms} ms`,
        tone: 'error',
        active: run.run_id === props.selectedRunId,
      }))
    case 'slow-runs':
      return slowRuns.value.slice(0, 10).map((run) => ({
        id: run.run_id,
        title: run.subscription_name,
        meta: `${run.site || 'unknown'} · ${run.status}`,
        value: `${run.duration_ms} ms`,
        tone: run.status === 'failed' ? 'error' : 'warning',
        active: run.run_id === props.selectedRunId,
      }))
    case 'recovery':
      return [
        {
          id: 'total',
          title: '恢复总数',
          meta: props.recoverySummary.last_reconcile_at || '未执行对账',
          value: props.recoverySummary.total_recovered || 0,
          tone: props.recoverySummary.total_recovered ? 'warning' : 'neutral',
        },
        {
          id: 'queued',
          title: 'queued 恢复',
          meta: '缺失消息或排队残留',
          value: props.recoverySummary.by_type?.stale_queued_recovered || 0,
          tone: 'warning',
        },
        {
          id: 'running',
          title: 'running 恢复',
          meta: '超时或锁残留',
          value: props.recoverySummary.by_type?.stale_running_recovered || 0,
          tone: 'info',
        },
      ]
    default:
      return []
  }
})

const showTrendPanel = computed(() => props.focus !== 'failed-runs')

const summaryMetrics = computed(() => {
  switch (props.focus) {
    case 'site':
      return [
        { label: '站点', value: props.site || '—' },
        { label: '运行', value: selectedSiteBreakdown.value?.runs_total || 0 },
        { label: '失败', value: selectedSiteBreakdown.value?.runs_failed || 0 },
        { label: '提取', value: selectedSiteBreakdown.value?.videos_extracted || 0 },
      ]
    case 'failed-runs':
      return [
        { label: '失败批次', value: failedRuns.value.length },
        { label: '当前选中', value: props.selectedRun?.run_id || '—' },
        { label: '最新错误', value: props.selectedRun?.error_type || '—' },
        { label: '待处理', value: props.selectedRun?.pending_video_count || 0 },
      ]
    case 'slow-runs':
      return [
        { label: '慢批次', value: slowRuns.value.length },
        { label: '最慢耗时', value: slowRuns.value[0] ? `${slowRuns.value[0].duration_ms} ms` : '—' },
        { label: '最高 P95', value: `${highestP95.value} ms` },
        { label: '当前选中', value: props.selectedRun?.run_id || '—' },
      ]
    case 'recovery':
      return [
        { label: '最近对账', value: props.recoverySummary.last_reconcile_at || '—' },
        { label: '恢复总数', value: props.recoverySummary.total_recovered || 0 },
        { label: 'queued', value: props.recoverySummary.by_type?.stale_queued_recovered || 0 },
        { label: 'running', value: props.recoverySummary.by_type?.stale_running_recovered || 0 },
      ]
    default:
      return []
  }
})

const handleObjectRowClick = (row: ObjectRow) => {
  if (props.focus === 'site') {
    emit('focus-site', row.id)
    return
  }
  if (props.focus === 'recovery') {
    emit('open-recovery')
    return
  }
  emit('open-run', row.id)
}

const getValueClass = (tone: AnalysisTone) => {
  switch (tone) {
    case 'error':
      return 'text-color-error'
    case 'info':
      return 'text-color-info'
    case 'warning':
      return 'text-color-warning'
    case 'success':
      return 'text-color-success'
    default:
      return 'text-text-primary'
  }
}

const getDotClass = (tone: AnalysisTone) => {
  switch (tone) {
    case 'error':
      return 'bg-color-error'
    case 'info':
      return 'bg-color-info'
    case 'warning':
      return 'bg-color-warning'
    case 'success':
      return 'bg-color-success'
    default:
      return 'bg-text-muted'
  }
}

const formatRunSummary = (run: SyncRunItem) => {
  const foundLabel = run.sync_mode === 'incremental' ? '新增' : '发现'
  return `${foundLabel} ${run.videos_found} · 入队 ${run.videos_enqueued} · 提取 ${run.videos_extracted}`
}
</script>
