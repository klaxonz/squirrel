<template>
  <div class="sync-center-page bg-bg-primary text-text-primary h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-6 pb-4">
      <div class="flex flex-col gap-5">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 class="text-2xl font-semibold text-text-primary">同步中心</h1>
            <p class="text-sm text-text-muted mt-1">集中处理失败订阅、排队状态和即将执行项。</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <div class="px-3 py-1.5 rounded-full bg-bg-secondary border border-border-primary text-text-tertiary">
              更新 {{ lastUpdatedAt || '—' }}
            </div>
            <div class="px-3 py-1.5 rounded-full bg-bg-secondary border border-border-primary text-text-tertiary">
              延后 {{ overview.deferred_count || 0 }}
            </div>
            <label class="px-3 py-1.5 rounded-full bg-bg-secondary border border-border-primary text-text-secondary inline-flex items-center gap-2 cursor-pointer">
              <input
                v-model="autoRefresh"
                type="checkbox"
                class="h-3.5 w-3.5 rounded border-border-primary bg-bg-primary"
              >
              自动刷新
            </label>
            <Button
              size="sm"
              shape="pill"
              variant="secondary"
              :loading="loadingOverview || loadingItems"
              @click="refreshAll"
            >
              刷新
            </Button>
            <Button
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

        <div class="grid grid-cols-1 xl:grid-cols-[1.2fr_1fr_1.2fr] gap-3">
          <div class="min-w-0">
            <Select
              size="sm"
              :model-value="filters.status"
              :options="statusOptions"
              @update:model-value="(value) => selectStatus(value)"
            />
          </div>
          <div class="min-w-0">
            <Select
              size="sm"
              :model-value="filters.site"
              :options="siteSelectOptions"
              @update:model-value="(value) => setSite(String(value || ''))"
            />
          </div>
          <div class="min-w-0">
            <input
              :value="filters.query"
              type="text"
              placeholder="搜索订阅..."
              class="w-full px-3 py-2 text-sm rounded-lg bg-bg-secondary border border-border-primary text-text-primary placeholder-text-muted focus:outline-none focus:border-border-hover focus:ring-1 focus:ring-border-hover"
              @input="handleQueryInput"
            >
          </div>
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

        <InlineAlert
          v-if="pageError"
          :message="pageError"
          action-label="重试"
          @action="refreshAll"
        />

        <SyncOverviewCards
          :overview="overview"
          :selected-status="filters.status"
          @select-status="selectStatus"
        />

        <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1.7fr)_minmax(20rem,0.9fr)] gap-4 flex-1 min-h-0">
          <div class="min-h-0 overflow-hidden">
            <SyncItemsPanel
              :active-status="filters.status"
              :items="items"
              :loading="loadingItems"
              :page="page"
              :page-size="pageSize"
              :retrying-id="retryingItemId"
              :total="total"
              @change-page="setPage"
              @change-status="selectStatus"
              @open-item="openDetail"
              @retry-item="handleRetryItem"
            />
          </div>

          <div class="space-y-4 min-h-0 overflow-y-auto pr-1">
            <Card class="p-4">
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm font-medium text-text-primary">运行中</span>
                <span class="text-xs text-text-tertiary">{{ runningPreview.length }} 条</span>
              </div>
              <div v-if="runningPreviewError" class="text-xs text-color-error mb-3">
                {{ runningPreviewError }}
              </div>
              <div v-if="runningPreview.length" class="space-y-3">
                <button
                  v-for="item in runningPreview"
                  :key="`running-${item.subscription_id}`"
                  type="button"
                  class="w-full text-left p-3 rounded-xl bg-bg-elevated hover:bg-bg-hover transition-colors"
                  @click="openDetail(item)"
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
              <div v-if="queuedPreviewError" class="text-xs text-color-error mb-3">
                {{ queuedPreviewError }}
              </div>
              <div v-if="queuedPreview.length" class="space-y-3">
                <button
                  v-for="item in queuedPreview"
                  :key="`queued-${item.subscription_id}`"
                  type="button"
                  class="w-full text-left p-3 rounded-xl bg-bg-elevated hover:bg-bg-hover transition-colors"
                  @click="openDetail(item)"
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
      </div>
    </div>

    <SyncDetailDrawer
      :item="selectedItem"
      :open="!!selectedItem"
      :retrying="retryingItemId === selectedItem?.subscription_id"
      @close="closeDetail"
      @retry="handleRetrySelected"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { Button, Card, InlineAlert, Select, StatusBadge } from '@/components/common'
import SyncDetailDrawer from '@/components/sync-center/SyncDetailDrawer.vue'
import SyncItemsPanel from '@/components/sync-center/SyncItemsPanel.vue'
import SyncOverviewCards from '@/components/sync-center/SyncOverviewCards.vue'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useSyncCenter } from '@/composables/useSyncCenter'

const {
  autoRefresh,
  closeDetail,
  filters,
  filteredFailedCount,
  items,
  lastUpdatedAt,
  loadingItems,
  loadingOverview,
  openDetail,
  overview,
  page,
  pageError,
  pageSize,
  queuedPreview,
  queuedPreviewError,
  refreshAll,
  retryFailed,
  retryingBatch,
  retryingItemId,
  retryItem,
  runningPreview,
  runningPreviewError,
  selectStatus,
  selectedItem,
  setPage,
  setQuery,
  setSite,
  siteOptions,
  statusOptions,
  total,
} = useSyncCenter()

const actionNotice = reactive({
  message: '',
  variant: 'success',
})

const siteSelectOptions = computed(() => ([
  { value: '', label: '全部站点' },
  ...siteOptions.value,
]))

const retryTargetCount = computed(() => {
  return filters.status === 'failed' ? total.value : filteredFailedCount.value
})

const handleQueryInput = (event: Event) => {
  const target = event.target as HTMLInputElement | null
  setQuery(target?.value || '')
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
  if (!selectedItem.value) {
    return
  }
  const result = await retryItem(selectedItem.value)
  if (result.error) {
    actionNotice.message = result.error.message || '重试失败'
    actionNotice.variant = 'error'
    return
  }
  actionNotice.message = `已提交重试：${selectedItem.value.subscription_name}`
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
</script>
