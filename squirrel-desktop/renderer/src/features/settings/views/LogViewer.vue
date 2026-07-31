<template>
  <AppPageShell class="log-viewer" variant="compact" surface="operate" width="table" fill>
    <div class="log-page">
      <main class="app-page-content log-content">
        <AppOperatePageHeader
          title="日志"
          :summary="logSummary"
          description="检查服务运行记录、请求追踪与异常上下文。"
        >
          <template #actions>
            <Button
              type="button"
              severity="secondary" outlined
              size="sm"
              :class="{ 'is-active': allCopied }"
              :disabled="logs.length === 0"
              :title="allCopied ? '已复制当前结果' : `复制当前显示的 ${logs.length} 条日志`"
              aria-label="复制当前日志结果"
              @click="copyAllLogs"
            >
              <AppIcon name="clipboard" class="h-4 w-4" />
              {{ allCopied ? '已复制' : '复制结果' }}
            </Button>

            <Button
              type="button"
              size="sm"
              :disabled="loading"
              title="立即刷新"
              aria-label="立即刷新日志"
              @click="loadLogs"
            >
              <AppSpinner v-if="loading" size="sm" />
              <AppIcon v-else name="refresh" class="h-4 w-4" />
              {{ loading ? '刷新中…' : '刷新日志' }}
            </Button>
          </template>
        </AppOperatePageHeader>

        <div class="log-filterbar">
          <AppSectionNav
            :model-value="filters.level"
            :options="levelFilterOptions"
            aria-label="日志级别"
            @change="setLevelFilter(String($event))"
          />

          <div class="log-filterbar__controls">
            <Select
              :model-value="filters.filename"
              :options="fileOptions"
              option-label="label"
              option-value="value"
              placeholder="选择日志文件"
              size="small"
              class="log-filterbar__file"
              aria-label="选择日志文件"
              @update:model-value="setFileFilter"
            />

            <label class="log-auto-refresh">
              <span>自动刷新</span>
              <Switch
                :model-value="autoRefresh"
                aria-label="每 5 秒自动刷新日志"
                @update:model-value="setAutoRefresh"
              />
            </label>

            <Button
              v-if="hasActiveFilters"
              type="button"
              size="sm"
              text severity="secondary"
              class="log-filterbar__clear"
              title="清空筛选"
              @click="clearFilters"
            >
              <AppIcon name="close" class="h-4 w-4" />
              清除筛选
            </Button>
          </div>
        </div>

        <section class="log-feed app-settings-panel" aria-label="系统日志工作区">
          <header class="log-feed__head">
            <div class="log-feed__heading">
              <h2>{{ filters.filename || '日志记录' }}</h2>
              <p aria-label="日志结果概览">
                <span>{{ resultSummary }}</span>
                <span>{{ activeLevelLabel }}</span>
                <span v-if="filters.keyword">搜索“{{ filters.keyword }}”</span>
                <span v-if="selectedFile">{{ formatFileSize(selectedFile.size) }}</span>
              </p>
            </div>
            <span v-if="lastLoadedAt" class="log-feed__updated">
              更新于 {{ formatLoadedTime(lastLoadedAt) }}
            </span>
          </header>

          <div class="log-columns" aria-hidden="true">
            <span>时间</span>
            <span>级别</span>
            <span>来源</span>
            <span>内容</span>
            <span />
          </div>

          <div class="log-stream">
            <div v-if="loading && logs.length === 0" class="log-loading">
              <AppSpinner size="sm" />
              <span>正在读取日志</span>
            </div>

            <AppEmptyState
              v-else-if="loadError"
              class="log-empty-state"
              variant="error"
              title="日志加载失败"
              :copy="loadError"
            >
              <template #actions>
                <Button size="sm" @click="loadLogs">重试</Button>
              </template>
            </AppEmptyState>

            <AppEmptyState
              v-else-if="logs.length === 0"
              class="log-empty-state"
              variant="plain"
              icon="inbox"
              :title="hasActiveFilters ? '没有匹配的日志' : '暂无日志'"
              :copy="hasActiveFilters ? '当前筛选条件没有结果。' : '当前日志文件中没有可显示的记录。'"
            >
              <template #actions>
                <Button
                  v-if="hasActiveFilters"
                  size="sm"
                  severity="secondary"
                  @click="clearFilters"
                >
                  清空筛选
                </Button>
                <Button size="sm" @click="loadLogs">刷新</Button>
              </template>
            </AppEmptyState>

            <DynamicScroller
              v-else
              :items="logs"
              :min-item-size="38"
              key-field="id"
              class="log-scroller custom-scrollbar"
            >
              <template v-slot="{ item, index, active }">
                <DynamicScrollerItem
                  :item="item"
                  :active="active"
                  :size-dependencies="[item.message]"
                  :data-index="index"
                >
                  <div class="log-row">
                    <time class="log-time" :datetime="item.timestamp">
                      {{ formatLogTimestamp(item.timestamp) }}
                    </time>

                    <span class="log-level" :data-level="item.level">
                      {{ item.level }}
                    </span>

                    <div class="log-source" :title="`${item.logger}:${item.line_num}`">
                      <span class="log-source__name">{{ item.logger }}</span>
                      <span class="log-source__line">:{{ item.line_num }}</span>
                    </div>

                    <div class="log-message">
                      <button
                        v-if="item.trace_id"
                        type="button"
                        class="log-trace"
                        :title="`筛选追踪编号 ${item.trace_id}`"
                        @click="filterByTraceId(item.trace_id)"
                      >
                        {{ item.trace_id.substring(0, 8) }}
                      </button>
                      <span>{{ item.message }}</span>
                    </div>

                    <Button
                      size="sm" icon-only
                      text severity="secondary"
                      class="log-row-copy"
                      title="复制这条日志"
                      aria-label="复制这条日志"
                      @click="copyLog(item)"
                    >
                      <AppIcon name="clipboard" class="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </DynamicScrollerItem>
              </template>
            </DynamicScroller>
          </div>
        </section>
      </main>
    </div>
  </AppPageShell>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppOperatePageHeader from '@/shared/components/layout/AppOperatePageHeader.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import { Button } from '@/shared/ui/button'
import { Select } from '@/shared/ui/select'
import { Switch } from '@/shared/ui/switch'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { getLogFiles, queryLogs } from '@/shared/api'
import { errorMessage } from '@/shared/lib/errorMessage'
import { Logger } from '@/shared/lib/logger'
import { useUIStore } from '@/shared/stores/ui'
import { useLogClipboard } from '@/features/settings/composables/useLogClipboard'
import { useLogAutoRefresh } from '@/features/settings/composables/useLogAutoRefresh'
import { formatFileSize, formatLogTimestamp } from '@/features/settings/lib/logPresenters'

const SEARCH_SCOPE = 'logs'
const LEVEL_FILTER_ALL = 'all'
const uiStore = useUIStore()
const logs = ref([])
const logFiles = ref([])
const totalLogs = ref(0)
const lastLoadedAt = ref(null)
const loading = ref(false)
const loadError = ref('')
let latestRequestId = 0

const filters = ref({
  keyword: uiStore.getSearchQuery(SEARCH_SCOPE).trim(),
  level: LEVEL_FILTER_ALL,
  filename: 'app.log',
})

const searchQuery = computed(() => uiStore.getSearchQuery(SEARCH_SCOPE))
const searchTrigger = computed(() => uiStore.getSearchTrigger(SEARCH_SCOPE))

const levelFilterOptions = [
  { value: LEVEL_FILTER_ALL, label: '全部' },
  { value: 'DEBUG', label: '调试' },
  { value: 'INFO', label: '信息' },
  { value: 'WARNING', label: '警告' },
  { value: 'ERROR', label: '错误' },
  { value: 'CRITICAL', label: '严重' },
]

const fileOptions = computed(() => {
  return logFiles.value.map((file) => ({
    value: file.name,
    // The active file size changes while the desktop app writes logs, so keep
    // the selector stable and surface size in the result summary instead.
    label: file.name,
  }))
})

const selectedFile = computed(() => (
  logFiles.value.find(file => file.name === filters.value.filename) || null
))

const logSummary = computed(() => (
  loading.value && logs.value.length === 0
    ? '读取中'
    : `${totalLogs.value.toLocaleString()} 条记录`
))

const activeLevelLabel = computed(() => (
  levelFilterOptions.find(option => option.value === filters.value.level)?.label || '全部'
))

const resultSummary = computed(() => {
  const visible = logs.value.length.toLocaleString()
  const total = totalLogs.value.toLocaleString()
  return logs.value.length < totalLogs.value
    ? `显示 ${visible} / ${total} 条`
    : `${total} 条结果`
})

const hasActiveFilters = computed(() => Boolean(
  filters.value.keyword || filters.value.level !== LEVEL_FILTER_ALL,
))

onMounted(() => {
  loadLogFiles()
  loadLogs()
})

watch(searchTrigger, () => {
  filters.value.keyword = searchQuery.value.trim()
  loadLogs()
})

async function loadLogFiles() {
  try {
    const data = await getLogFiles()
    logFiles.value = data || []
    if (logFiles.value.length > 0 && !filters.value.filename) {
      filters.value.filename = logFiles.value[0].name
    }
  } catch (error) {
    Logger.error('Failed to load log files', error)
  }
}

async function loadLogs() {
  const requestId = ++latestRequestId
  loading.value = true
  loadError.value = ''
  try {
    const params = {
      filename: filters.value.filename,
      keyword: filters.value.keyword || undefined,
      level: filters.value.level === LEVEL_FILTER_ALL ? undefined : filters.value.level,
      page: 1,
      pageSize: 500,
    }
    const data = await queryLogs(params)
    if (data && requestId === latestRequestId) {
      logs.value = data.logs.map((log, index) => ({
        ...log,
        id: `${Date.now()}-${index}-${log.line_num}`,
      }))
      totalLogs.value = Number.isFinite(data.total) ? data.total : logs.value.length
      lastLoadedAt.value = new Date()
      loadError.value = ''
    }
  } catch (error) {
    Logger.error('Failed to load logs', error)
    if (requestId === latestRequestId) {
      logs.value = []
      totalLogs.value = 0
      loadError.value = errorMessage(error, '无法读取日志，请检查后端连接后重试。')
    }
  } finally {
    if (requestId === latestRequestId) {
      loading.value = false
    }
  }
}

function clearFilters() {
  filters.value.level = LEVEL_FILTER_ALL
  uiStore.triggerSearch(SEARCH_SCOPE, '')
}

function filterByTraceId(traceId) {
  filters.value.level = LEVEL_FILTER_ALL
  uiStore.triggerSearch(SEARCH_SCOPE, traceId)
}

function setLevelFilter(value) {
  filters.value.level = value
  loadLogs()
}

function setFileFilter(value) {
  filters.value.filename = value
  loadLogs()
}

function setAutoRefresh(enabled) {
  if (enabled !== autoRefresh.value) toggleAutoRefresh()
}

function formatLoadedTime(date) {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const { allCopied, copyLog, copyAllLogs } = useLogClipboard({ logs, filters })
const { autoRefresh, toggleAutoRefresh } = useLogAutoRefresh({ refresh: loadLogs })
</script>

<style scoped>
.log-viewer {
  --app-page-max-width: var(--app-content-table-max);
  min-height: 0;
}

.log-page {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
}

.log-content {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--space-5);
  padding-top: var(--space-7);
  padding-bottom: var(--space-7);
}

.log-filterbar {
  display: flex;
  width: 100%;
  min-width: 0;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  padding: 0.5rem 0.75rem;
}

.log-filterbar__controls {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.log-filterbar__file {
  width: 13.5rem;
}

.log-auto-refresh {
  display: inline-flex;
  min-height: 2rem;
  align-items: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.log-filterbar__clear {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.log-feed {
  --log-grid-columns: 7.5rem 4.75rem minmax(9rem, 13rem) minmax(18rem, 1fr) 2rem;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
}

.log-feed__head {
  display: flex;
  min-height: 3.5rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border-bottom: 1px solid hsl(var(--border));
  padding: 0.75rem var(--space-4);
}

.log-feed__heading {
  display: grid;
  min-width: 0;
  gap: 0.3rem;
}

.log-feed__heading h2 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 700;
}

.log-feed__heading p {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  margin: 0;
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
}

.log-feed__heading p span + span::before {
  margin-right: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.34);
  content: '·';
}

.log-feed__updated {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.log-columns,
.log-row {
  display: grid;
  grid-template-columns: var(--log-grid-columns);
  column-gap: var(--space-3);
}

.log-columns {
  flex: none;
  align-items: center;
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--muted) / 0.14);
  padding: 0.4375rem 0.75rem;
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: 0.6875rem;
  font-weight: 650;
}

.log-stream {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-mono);
}

.log-scroller {
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
}

.log-row {
  position: relative;
  min-height: 2.75rem;
  align-items: start;
  border-bottom: 1px solid hsl(var(--border) / 0.26);
  padding: 0.5rem 0.75rem;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.log-row:hover,
.log-row:focus-within {
  background: hsl(var(--muted) / 0.22);
}

.log-time {
  padding-top: 0.125rem;
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.log-level {
  display: inline-flex;
  width: fit-content;
  min-width: 3.75rem;
  min-height: 1.25rem;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border) / 0.52);
  border-radius: var(--radius-sm);
  background: hsl(var(--foreground) / 0.035);
  padding: 0 0.375rem;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.6875rem;
  font-weight: 650;
  line-height: 1;
}

.log-level[data-level='DEBUG'] {
  color: hsl(var(--muted-foreground) / 0.52);
}

.log-level[data-level='INFO'] {
  border-color: hsl(var(--foreground) / 0.08);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.72);
}

.log-level[data-level='WARNING'] {
  border-color: hsl(var(--warning) / 0.28);
  background: hsl(var(--warning) / 0.1);
  color: hsl(var(--warning));
}

.log-level[data-level='ERROR'],
.log-level[data-level='CRITICAL'] {
  border-color: hsl(var(--destructive) / 0.3);
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.log-level[data-level='CRITICAL'] {
  font-weight: 800;
}

.log-source {
  display: flex;
  min-width: 0;
  align-items: baseline;
  padding-top: 0.0625rem;
  color: hsl(var(--muted-foreground) / 0.64);
  font-size: 0.75rem;
}

.log-source__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-source__line {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.48);
}

.log-message {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: var(--space-2);
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-trace {
  flex: none;
  min-height: 1.25rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-sm);
  background: hsl(var(--foreground) / 0.03);
  padding: 0 0.3125rem;
  color: hsl(var(--muted-foreground));
  font: inherit;
  font-size: var(--app-text-badge-size);
  line-height: 1.125rem;
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.log-trace:hover {
  border-color: var(--app-selection-border-hover);
  background: var(--app-selection-bg-hover);
  color: hsl(var(--foreground));
}

.log-trace:focus-visible {
  outline: 2px solid hsl(var(--ring) / 0.48);
  outline-offset: 1px;
}

.log-row-copy {
  margin-top: -0.125rem;
  color: hsl(var(--muted-foreground) / 0.65);
  opacity: 0;
  transition:
    color var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.log-row:hover .log-row-copy,
.log-row:focus-within .log-row-copy {
  opacity: 1;
}

.log-loading {
  display: flex;
  min-height: 18rem;
  flex: 1 1 auto;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-family: var(--font-sans);
  font-size: 0.8125rem;
}

.log-empty-state {
  min-height: 18rem;
  flex: 1 1 auto;
  font-family: var(--font-sans);
}

@media (max-width: 1100px) {
  .log-filterbar {
    align-items: flex-end;
  }

  .log-feed {
    --log-grid-columns: 7rem 4.5rem minmax(8rem, 10rem) minmax(16rem, 1fr) 2rem;
  }

  .log-filterbar__file {
    width: 11.5rem;
  }
}

@media (max-width: 900px) {
  .log-filterbar {
    align-items: flex-start;
    flex-direction: column;
    padding-bottom: var(--space-2);
  }

  .log-filterbar__controls {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .log-feed {
    --log-grid-columns: 7rem 4.5rem minmax(16rem, 1fr) 2rem;
  }

  .log-columns > span:nth-child(3),
  .log-source {
    display: none;
  }

  .log-feed__updated {
    display: none;
  }
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .log-row-copy {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .log-row,
  .log-row-copy,
  .log-trace {
    transition: none;
  }
}
</style>
