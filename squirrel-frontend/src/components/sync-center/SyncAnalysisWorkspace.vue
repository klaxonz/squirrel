<template>
  <section class="grid min-h-0 grid-cols-1 gap-3 xl:h-[min(44rem,calc(var(--app-content-height)-18rem))] xl:grid-cols-[minmax(18rem,0.95fr)_minmax(0,1.35fr)]">
    <div
      class="min-h-0 xl:flex"
      :class="focus === 'overview' || focus === 'failed-runs' ? 'xl:col-span-2' : ''"
    >
      <SyncRunHistoryPanel
        class="min-h-0 flex-1"
        embedded
        :error="runsError"
        :filters="runFilters"
        :loading="runsLoading"
        :page="runPage"
        :page-size="runPageSize"
        :runs="runs"
        :selected-run-id="selectedRunId"
        :site-options="siteOptions"
        :subscription-options="subscriptionOptions"
        :total="runTotal"
        @change-page="emit('change-history-page', $event)"
        @open-run="emit('open-run', $event)"
        @set-filter="emit('change-history-filter', $event)"
      />
    </div>

    <aside
      v-if="focus !== 'overview' && focus !== 'failed-runs'"
      class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border-primary bg-bg-secondary"
    >
      <div class="flex items-center justify-between border-b border-border-primary px-3 py-2.5">
        <div class="min-w-0">
          <div class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">{{ workspaceLabel }}</div>
          <div class="mt-1 text-2xs text-text-muted">{{ workspaceMeta }}</div>
        </div>
        <div class="flex items-center gap-2">
          <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
            {{ objectRows.length }}
          </span>
        </div>
      </div>

      <div v-if="objectRows.length" class="min-h-0 flex-1 overflow-y-auto divide-y divide-border-primary">
        <div
          v-for="row in objectRows"
          :key="row.id"
          class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-bg-hover"
        >
          <router-link
            v-if="hasSubscription(row)"
            :to="getSubscriptionLink(row.subscriptionId)"
            class="shrink-0"
            @click.stop
          >
            <img
              :src="getAvatarSrc(row.avatar, getAvatarKey(row))"
              :alt="row.title"
              class="h-10 w-10 rounded-full object-cover bg-bg-primary ring-1 ring-border-primary"
              referrerpolicy="no-referrer"
              @error="(e) => handleAvatarError(e, getAvatarKey(row))"
            >
          </router-link>
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
            :class="row.active ? 'bg-bg-hover' : ''"
            @click="handleObjectRowClick(row)"
          >
            <div class="min-w-0">
              <div class="text-xs font-medium leading-5 text-text-primary break-words">{{ row.title }}</div>
              <div class="mt-0.5 text-2xs leading-5 text-text-tertiary break-words">{{ row.meta }}</div>
            </div>
            <div class="flex shrink-0 items-center">
              <span class="text-xs font-semibold" :class="getValueClass(row.tone)">{{ row.value }}</span>
            </div>
          </button>
        </div>
      </div>
      <div v-else class="px-3 py-6 text-center text-2xs text-text-muted">
        当前没有可分析对象
      </div>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SyncRunHistoryPanel from '@/components/sync-center/SyncRunHistoryPanel.vue'
import type { SyncFocusKind } from '@/composables/useSyncCenterWorkbench'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import type { SyncTrendSiteBreakdown } from '@/composables/useSyncTrends'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDurationMs } from '@/utils/dateFormat'

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
  avatar?: string | null
  subscriptionId?: number | null
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
  siteOptions: Array<{ value: string; label: string }>
  subscriptionOptions: Array<{ value: string; label: string; avatar: string | null }>
  siteBreakdown: SyncTrendSiteBreakdown[]
  selectedRunId: string
  recoverySummary: RecoverySummary
}>()

const emit = defineEmits<{
  (e: 'change-history-filter', payload: { key: string; value: string }): void
  (e: 'change-history-page', page: number): void
  (e: 'focus-site', site: string): void
  (e: 'open-recovery'): void
  (e: 'open-run', runId: string): void
}>()

const failedRuns = computed(() => props.runs.filter((run) => run.status === 'failed'))
const slowRuns = computed(() => [...props.runs].sort((left, right) => right.duration_ms - left.duration_ms))
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()

const workspaceLabel = computed(() => {
  switch (props.focus) {
    case 'site':
      return '站点异常明细'
    case 'failed-runs':
      return '失败运行明细'
    case 'slow-runs':
      return '高延迟运行明细'
    case 'recovery':
      return '恢复异常明细'
    default:
      return '处理工作台'
  }
})

const workspaceMeta = computed(() => {
  switch (props.focus) {
    case 'site':
      return props.site ? `聚焦站点 ${props.site}` : '选择一个异常站点查看影响面'
    case 'failed-runs':
      return '查看最近失败运行与关联订阅'
    case 'slow-runs':
      return '查看耗时偏高的运行与关联订阅'
    case 'recovery':
      return `查看最近 ${props.recoverySummary.window_hours}h 的恢复动作`
    default:
      return '从总览进入具体处理模式'
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
        meta: `${run.site || 'unknown'} ${run.last_event_at || run.finished_at || '—'}`,
        value: formatDurationMs(run.duration_ms),
        tone: 'error',
        active: run.run_id === props.selectedRunId,
        avatar: run.subscription_avatar,
        subscriptionId: run.subscription_id,
      }))
    case 'slow-runs':
      return slowRuns.value.slice(0, 10).map((run) => ({
        id: run.run_id,
        title: run.subscription_name,
        meta: `${run.site || 'unknown'} · ${run.status}`,
        value: formatDurationMs(run.duration_ms),
        tone: run.status === 'failed' ? 'error' : 'warning',
        active: run.run_id === props.selectedRunId,
        avatar: run.subscription_avatar,
        subscriptionId: run.subscription_id,
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

const hasSubscription = (row: ObjectRow) => row.subscriptionId != null

const getSubscriptionLink = (subscriptionId: number | null | undefined) => `/subscription/${subscriptionId}/all`

const getAvatarKey = (row: ObjectRow) => `${props.focus}-${row.id}`

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

</script>
