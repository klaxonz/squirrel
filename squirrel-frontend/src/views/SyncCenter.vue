<template>
  <div class="sync-center-page bg-bg-primary text-text-primary h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-6 pb-4">
      <div class="flex flex-col gap-5">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 class="text-2xl font-semibold text-text-primary">同步中心</h1>
            <p class="text-sm text-text-muted mt-1">{{ tabDescription }}</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <div class="px-3 py-1.5 rounded-full bg-bg-secondary border border-border-primary text-text-tertiary">
              更新 {{ toolbarLastUpdatedAt || '—' }}
            </div>
            <label
              v-if="activeTab === 'overview'"
              class="px-3 py-1.5 rounded-full bg-bg-secondary border border-border-primary text-text-secondary inline-flex items-center gap-2 cursor-pointer"
            >
              <input
                v-model="overviewAutoRefresh"
                type="checkbox"
                class="h-3.5 w-3.5 rounded border-border-primary bg-bg-primary"
              >
              自动刷新
            </label>
            <Button
              size="sm"
              shape="pill"
              variant="secondary"
              :loading="toolbarLoading"
              @click="handleRefreshCurrentTab"
            >
              刷新
            </Button>
            <Button
              v-if="activeTab === 'overview'"
              size="sm"
              shape="pill"
              variant="primary"
              :disabled="retryTargetCount === 0"
              :loading="retryingBatch"
              @click="handleRetryFailed"
            >
              重试筛选失败项
            </Button>
          </div>
        </div>

        <div class="inline-flex items-center gap-1 p-1 rounded-full bg-bg-secondary border border-border-primary self-start">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="px-4 py-2 text-sm font-medium rounded-full transition-colors"
            :class="activeTab === tab.key
              ? 'bg-bg-elevated text-text-primary shadow-sm'
              : 'text-text-muted hover:text-text-primary hover:bg-bg-hover'"
            @click="handleChangeTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
    </div>

    <div class="content-container pb-8 flex-1 min-h-0 overflow-hidden">
      <div class="space-y-4 h-full flex flex-col min-h-0">
        <InlineAlert
          v-if="actionNotice.message"
          :message="actionNotice.message"
          :variant="actionNotice.variant"
        />

        <template v-if="activeTab === 'overview'">
          <InlineAlert
            v-if="overviewPageError"
            :message="overviewPageError"
            action-label="重试"
            @action="overviewRefreshAll"
          />

          <div class="grid grid-cols-1 xl:grid-cols-[1.2fr_1fr_1.2fr] gap-3">
            <div class="min-w-0">
              <Select
                size="sm"
                :model-value="overviewFilters.status"
                :options="overviewStatusOptions"
                @update:model-value="(value) => overviewSelectStatus(value)"
              />
            </div>
            <div class="min-w-0">
              <Select
                size="sm"
                :model-value="overviewFilters.site"
                :options="siteSelectOptions"
                @update:model-value="(value) => overviewSetSite(String(value || ''))"
              />
            </div>
            <div class="min-w-0">
              <input
                :value="overviewFilters.query"
                type="text"
                placeholder="搜索订阅..."
                class="w-full px-3 py-2 text-sm rounded-lg bg-bg-secondary border border-border-primary text-text-primary placeholder-text-muted focus:outline-none focus:border-border-hover focus:ring-1 focus:ring-border-hover"
                @input="handleOverviewQueryInput"
              >
            </div>
          </div>

          <SyncOverviewCards
            :overview="overview"
            :selected-status="overviewFilters.status"
            @select-status="overviewSelectStatus"
          />

          <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1.7fr)_minmax(20rem,0.9fr)] gap-4 flex-1 min-h-0">
            <div class="min-h-0 overflow-hidden">
              <SyncItemsPanel
                :active-status="overviewFilters.status"
                :items="overviewItems"
                :loading="overviewLoadingItems"
                :page="overviewPage"
                :page-size="overviewPageSize"
                :retrying-id="retryingItemId"
                :total="overviewTotal"
                @change-page="overviewSetPage"
                @change-status="overviewSelectStatus"
                @open-item="overviewOpenDetail"
                @retry-item="handleRetryItem"
              />
            </div>

            <div class="space-y-4 min-h-0 overflow-y-auto pr-1">
              <Card class="p-4">
                <div class="flex items-center justify-between mb-3">
                  <span class="text-sm font-medium text-text-primary">运行中</span>
                  <span class="text-xs text-text-tertiary">{{ runningPreview.length }} 条</span>
                </div>
                <div v-if="runningPreviewError" class="text-xs text-color-error mb-3">{{ runningPreviewError }}</div>
                <div v-if="runningPreview.length" class="space-y-3">
                  <button
                    v-for="item in runningPreview"
                    :key="`running-${item.subscription_id}`"
                    type="button"
                    class="w-full text-left p-3 rounded-xl bg-bg-elevated hover:bg-bg-hover transition-colors"
                    @click="overviewOpenDetail(item)"
                  >
                    <div class="flex items-center justify-between gap-3">
                      <div class="min-w-0">
                        <div class="text-sm text-text-primary truncate">{{ item.subscription_name }}</div>
                        <div class="text-2xs text-text-tertiary mt-1">
                          {{ item.site || 'unknown' }} · {{ item.sync_mode === 'full' ? 'Full' : 'Incr' }}
                        </div>
                      </div>
                      <StatusBadge size="xs" :show-dot="false" variant="info" label="运行中" class="border-0" />
                    </div>
                    <div class="text-2xs text-text-muted mt-2">
                      {{ item.locked_at || item.updated_at || '刚刚开始' }} · 待处理 {{ item.pending_video_count || 0 }}
                    </div>
                  </button>
                </div>
                <div v-else class="text-xs text-text-muted">当前没有运行中的同步任务。</div>
              </Card>

              <Card class="p-4">
                <div class="flex items-center justify-between mb-3">
                  <span class="text-sm font-medium text-text-primary">排队概览</span>
                  <span class="text-xs text-text-tertiary">{{ queuedPreview.length }} 条</span>
                </div>
                <div v-if="queuedPreviewError" class="text-xs text-color-error mb-3">{{ queuedPreviewError }}</div>
                <div v-if="queuedPreview.length" class="space-y-3">
                  <button
                    v-for="item in queuedPreview"
                    :key="`queued-${item.subscription_id}`"
                    type="button"
                    class="w-full text-left p-3 rounded-xl bg-bg-elevated hover:bg-bg-hover transition-colors"
                    @click="overviewOpenDetail(item)"
                  >
                    <div class="flex items-center justify-between gap-3">
                      <div class="min-w-0">
                        <div class="text-sm text-text-primary truncate">{{ item.subscription_name }}</div>
                        <div class="text-2xs text-text-tertiary mt-1">
                          {{ item.site || 'unknown' }} · {{ item.sync_mode === 'full' ? 'Full' : 'Incr' }}
                        </div>
                      </div>
                      <StatusBadge size="xs" :show-dot="false" variant="warning" label="排队中" class="border-0" />
                    </div>
                    <div class="text-2xs text-text-muted mt-2">
                      {{ item.queued_at || item.updated_at || '等待入队消费' }} · 待处理 {{ item.pending_video_count || 0 }}
                    </div>
                  </button>
                </div>
                <div v-else class="text-xs text-text-muted">当前没有排队中的同步任务。</div>
              </Card>

              <Card class="p-4">
                <div class="flex items-center justify-between mb-3">
                  <span class="text-sm font-medium text-text-primary">系统视图</span>
                  <span class="text-xs text-text-tertiary">待处理 {{ overview.pending_videos }}</span>
                </div>
                <div class="space-y-3 text-xs">
                  <div class="flex items-center justify-between">
                    <span class="text-text-tertiary">失败待处理</span>
                    <span class="text-text-primary">{{ overview.failed_count }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-text-tertiary">即将执行</span>
                    <span class="text-text-primary">{{ overview.due_soon_count }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-text-tertiary">队列消息</span>
                    <span class="text-text-primary">{{ overview.queue_messages }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-text-tertiary">延后执行</span>
                    <span class="text-text-primary">{{ overview.deferred_count }}</span>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </template>

        <template v-else-if="activeTab === 'history'">
          <SyncRunHistoryPanel
            :error="historyError"
            :filters="historyFilters"
            :loading="historyLoading"
            :page="historyPage"
            :page-size="historyPageSize"
            :runs="historyRuns"
            :total="historyTotal"
            @change-page="historySetPage"
            @open-run="historySelectRun"
            @set-filter="handleHistoryFilter"
          />
          <SyncRunDetailDrawer
            :detail-error="historyDetailError"
            :detail-loading="historyDetailLoading"
            :events="historyEvents"
            :open="!!historySelectedRun"
            :run="historySelectedRun"
            @close="historyCloseRun"
          />
        </template>

        <template v-else>
          <SyncTrendCharts
            :error="trendError"
            :filters="trendFilters"
            :loading="trendLoading"
            :range="trendRange"
            :series="trendSeries"
            :site-breakdown="trendSiteBreakdown"
            @set-filter="handleTrendFilter"
            @set-range="handleTrendRange"
          />
        </template>
      </div>
    </div>

    <SyncDetailDrawer
      v-if="activeTab === 'overview'"
      :item="overviewSelectedItem"
      :open="!!overviewSelectedItem"
      :retrying="retryingItemId === overviewSelectedItem?.subscription_id"
      @close="overviewCloseDetail"
      @retry="handleRetrySelected"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Card, InlineAlert, Select, StatusBadge } from '@/components/common'
import SyncDetailDrawer from '@/components/sync-center/SyncDetailDrawer.vue'
import SyncItemsPanel from '@/components/sync-center/SyncItemsPanel.vue'
import SyncOverviewCards from '@/components/sync-center/SyncOverviewCards.vue'
import SyncRunDetailDrawer from '@/components/sync-center/SyncRunDetailDrawer.vue'
import SyncRunHistoryPanel from '@/components/sync-center/SyncRunHistoryPanel.vue'
import SyncTrendCharts from '@/components/sync-center/SyncTrendCharts.vue'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useSyncCenter } from '@/composables/useSyncCenter'
import { useSyncHistory } from '@/composables/useSyncHistory'
import { useSyncTrends } from '@/composables/useSyncTrends'

type SyncTabKey = 'overview' | 'history' | 'trends'

const tabs: Array<{ key: SyncTabKey; label: string }> = [
  { key: 'overview', label: '概览' },
  { key: 'history', label: '运行历史' },
  { key: 'trends', label: '趋势分析' },
]

const activeTab = ref<SyncTabKey>('overview')
const historyFilterTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const trendFilterTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const {
  autoRefresh: overviewAutoRefresh,
  closeDetail: overviewCloseDetail,
  filters: overviewFilters,
  filteredFailedCount,
  items: overviewItems,
  lastUpdatedAt: overviewLastUpdatedAt,
  loadingItems: overviewLoadingItems,
  loadingOverview,
  openDetail: overviewOpenDetail,
  overview,
  page: overviewPage,
  pageError: overviewPageError,
  pageSize: overviewPageSize,
  queuedPreview,
  queuedPreviewError,
  refreshAll: overviewRefreshAll,
  retryFailed,
  retryingBatch,
  retryingItemId,
  retryItem,
  runningPreview,
  runningPreviewError,
  setPollingEnabled,
  selectStatus: overviewSelectStatus,
  selectedItem: overviewSelectedItem,
  setPage: overviewSetPage,
  setQuery: overviewSetQuery,
  setSite: overviewSetSite,
  siteOptions,
  statusOptions: overviewStatusOptions,
  total: overviewTotal,
} = useSyncCenter()

const {
  closeRun: historyCloseRun,
  detailError: historyDetailError,
  detailLoading: historyDetailLoading,
  error: historyError,
  events: historyEvents,
  filters: historyFilters,
  lastUpdatedAt: historyLastUpdatedAt,
  loadRuns: historyLoadRuns,
  loading: historyLoading,
  page: historyPage,
  pageSize: historyPageSize,
  refreshSelectedRun: historyRefreshSelectedRun,
  runs: historyRuns,
  selectRun: historySelectRun,
  selectedRun: historySelectedRun,
  setPage: historySetPage,
  total: historyTotal,
} = useSyncHistory()

const {
  error: trendError,
  filters: trendFilters,
  lastUpdatedAt: trendLastUpdatedAt,
  loadTrends,
  loading: trendLoading,
  range: trendRange,
  series: trendSeries,
  siteBreakdown: trendSiteBreakdown,
} = useSyncTrends()

const actionNotice = reactive({
  message: '',
  variant: 'success',
})

const siteSelectOptions = computed(() => ([
  { value: '', label: '全部站点' },
  ...siteOptions.value,
]))

const retryTargetCount = computed(() => {
  return overviewFilters.status === 'failed' ? overviewTotal.value : filteredFailedCount.value
})

const toolbarLoading = computed(() => {
  if (activeTab.value === 'overview') {
    return loadingOverview.value || overviewLoadingItems.value
  }
  if (activeTab.value === 'history') {
    return historyLoading.value || historyDetailLoading.value
  }
  return trendLoading.value
})

const toolbarLastUpdatedAt = computed(() => {
  if (activeTab.value === 'history') {
    return historyLastUpdatedAt.value
  }
  if (activeTab.value === 'trends') {
    return trendLastUpdatedAt.value
  }
  return overviewLastUpdatedAt.value
})

const tabDescription = computed(() => {
  if (activeTab.value === 'history') {
    return '查看运行实例、阶段时间线和原始事件流。'
  }
  if (activeTab.value === 'trends') {
    return '按时间范围查看运行结果、吞吐和时延趋势。'
  }
  return '集中处理失败订阅、排队状态和即将执行项。'
})

const handleOverviewQueryInput = (event: Event) => {
  const target = event.target as HTMLInputElement | null
  overviewSetQuery(target?.value || '')
}

const handleRetryItem = async (item: SyncCenterItem) => {
  const result = await retryItem(item)
  if (result.error) {
    actionNotice.message = result.error.message || '重试失败'
    actionNotice.variant = 'error'
    return
  }
  actionNotice.message = `已提交重试：${item.subscription_name}`
  actionNotice.variant = 'success'
}

const handleRetrySelected = async () => {
  if (!overviewSelectedItem.value) {
    return
  }
  const result = await retryItem(overviewSelectedItem.value)
  if (result.error) {
    actionNotice.message = result.error.message || '重试失败'
    actionNotice.variant = 'error'
    return
  }
  actionNotice.message = `已提交重试：${overviewSelectedItem.value.subscription_name}`
  actionNotice.variant = 'success'
}

const handleRetryFailed = async () => {
  const { data, error } = await retryFailed()
  if (error) {
    actionNotice.message = error.message || '批量重试失败'
    actionNotice.variant = 'error'
    return
  }
  if (data) {
    actionNotice.message = `已处理 ${data.total} 项，入队 ${data.queued} 项，执行中 ${data.in_progress} 项，失败 ${data.failed} 项，跳过 ${data.skipped} 项`
    actionNotice.variant = data.failed > 0 ? 'warning' : 'success'
  }
}

const handleRefreshCurrentTab = async () => {
  if (activeTab.value === 'overview') {
    await overviewRefreshAll()
    return
  }
  if (activeTab.value === 'history') {
    await historyLoadRuns()
    await historyRefreshSelectedRun()
    return
  }
  await loadTrends()
}

const handleChangeTab = async (tab: SyncTabKey) => {
  activeTab.value = tab
  setPollingEnabled(tab === 'overview')
  if (tab === 'history' && historyRuns.value.length === 0) {
    await historyLoadRuns()
  }
  if (tab === 'trends' && trendSeries.value.length === 0) {
    await loadTrends()
  }
}

const handleHistoryFilter = async (key: string, value: string) => {
  historyFilters[key as keyof typeof historyFilters] = value
  historyPage.value = 1
  if (historyFilterTimer.value) {
    clearTimeout(historyFilterTimer.value)
    historyFilterTimer.value = null
  }
  if (key === 'site' || key === 'mode' || key === 'trigger') {
    historyFilterTimer.value = setTimeout(async () => {
      await historyLoadRuns()
    }, 250)
    return
  }
  await historyLoadRuns()
}

const handleTrendFilter = async (key: string, value: string) => {
  trendFilters[key as keyof typeof trendFilters] = value
  if (trendFilterTimer.value) {
    clearTimeout(trendFilterTimer.value)
    trendFilterTimer.value = null
  }
  trendFilterTimer.value = setTimeout(async () => {
    await loadTrends()
  }, 250)
}

const handleTrendRange = async (value: string) => {
  trendRange.value = value
  await loadTrends()
}

onMounted(() => {
  setPollingEnabled(activeTab.value === 'overview')
})
</script>
