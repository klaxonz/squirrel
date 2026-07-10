<template>
  <AppPageShell class="log-viewer" variant="compact" fill>
    <div class="log-page">
      <AppToolbarFrame bordered compact sticky>
      <form class="log-toolbar" role="search" @submit.prevent="applyKeywordFilter">
        <div class="log-toolbar__primary">
          <AppSearchInput
            :model-value="keywordDraft"
            class="log-toolbar__search"
            placeholder="搜索日志内容或追踪编号"
            aria-label="搜索日志内容或追踪编号"
            @update:model-value="updateKeywordDraft"
          />
        </div>

        <div class="log-toolbar__actions">
          <Select
            :model-value="filters.level"
            @update:model-value="setLevelFilter"
          >
            <SelectTrigger
              class="app-toolbar-control app-toolbar-select-trigger log-toolbar__level"
              :class="{ 'is-active': Boolean(filters.level) }"
              aria-label="按日志级别筛选"
            >
              <SelectValue placeholder="全部级别" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in levelOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>

          <Select
            :model-value="filters.filename"
            @update:model-value="setFileFilter"
          >
            <SelectTrigger
              class="app-toolbar-control app-toolbar-select-trigger log-toolbar__file"
              aria-label="选择日志文件"
            >
              <SelectValue placeholder="选择日志文件" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in fileOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>

          <Button
            v-if="hasActiveFilters"
            type="button"
            size="icon-sm"
            variant="ghost"
            class="app-toolbar-control app-toolbar-icon-button"
            title="清空筛选"
            aria-label="清空筛选"
            @click="clearFilters"
          >
            <AppIcon name="close" class="h-4 w-4" />
          </Button>

          <Button
            type="submit"
            size="sm"
            variant="ghost"
            class="log-toolbar__filter"
            :class="{ 'is-active': Boolean(filters.keyword) }"
          >
            <AppIcon name="filter" class="h-3.5 w-3.5" />
            筛选
          </Button>

          <div class="log-toolbar__divider" aria-hidden="true" />

          <label class="log-auto-refresh">
            <span>自动刷新</span>
            <Switch
              :model-value="autoRefresh"
              aria-label="每 5 秒自动刷新日志"
              @update:model-value="setAutoRefresh"
            />
          </label>

          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="app-toolbar-control app-toolbar-icon-button"
            :class="{ 'is-active': allCopied }"
            :disabled="logs.length === 0"
            :title="allCopied ? '已复制当前结果' : `复制当前显示的 ${logs.length} 条日志`"
            aria-label="复制当前日志结果"
            @click="copyAllLogs"
          >
            <AppIcon name="clipboard" class="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="app-toolbar-control app-toolbar-icon-button"
            :disabled="loading"
            title="立即刷新"
            aria-label="立即刷新日志"
            @click="loadLogs"
          >
            <AppSpinner v-if="loading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </Button>
        </div>
        </form>
      </AppToolbarFrame>

      <div class="app-page-content app-page-content--media log-content">
        <section class="log-feed" aria-label="系统日志工作区">
        <header class="log-feed__header">
          <div class="log-feed__identity">
            <div class="log-feed__title-row">
              <h2>{{ filters.filename || '系统日志' }}</h2>
              <span v-if="selectedFileSize">{{ selectedFileSize }}</span>
            </div>
            <p>{{ headerSubtitle }}</p>
          </div>

          <div class="log-feed__state" aria-live="polite">
            <span>{{ visibleCountLabel }}</span>
            <span class="log-feed__divider" aria-hidden="true" />
            <span class="log-live-state" :class="{ 'is-active': autoRefresh }">
              <span class="log-live-state__dot" />
              {{ loading ? '同步中' : autoRefresh ? '每 5 秒刷新' : '自动刷新已暂停' }}
            </span>
          </div>
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
                variant="secondary"
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
                    size="mini-icon"
                    variant="ghost"
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
      </div>
    </div>
  </AppPageShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import { Button } from '@/shared/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
import { Switch } from '@/shared/ui/switch'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { getLogFiles, queryLogs } from '@/shared/api'
import { Logger } from '@/shared/lib/logger'
import { useLogClipboard } from '@/features/settings/composables/useLogClipboard'
import { useLogAutoRefresh } from '@/features/settings/composables/useLogAutoRefresh'
import {
  formatFileSize,
  formatLogTimestamp,
} from '@/features/settings/lib/logPresenters'

const logs = ref([])
const logFiles = ref([])
const totalLogs = ref(0)
const loading = ref(false)
const keywordDraft = ref('')
let latestRequestId = 0

const filters = ref({
  keyword: '',
  level: '',
  filename: 'app.log',
})

const levelOptions = [
  { value: '', label: '全部级别' },
  { value: 'DEBUG', label: '调试' },
  { value: 'INFO', label: '信息' },
  { value: 'WARNING', label: '警告' },
  { value: 'ERROR', label: '错误' },
  { value: 'CRITICAL', label: '严重' },
]

const fileOptions = computed(() => {
  return logFiles.value.map((file) => ({
    value: file.name,
    label: `${file.name} · ${formatFileSize(file.size)}`,
  }))
})

const selectedFile = computed(() => {
  return logFiles.value.find((file) => file.name === filters.value.filename)
})

const selectedFileSize = computed(() => {
  return selectedFile.value ? formatFileSize(selectedFile.value.size) : ''
})

const hasActiveFilters = computed(() => Boolean(filters.value.keyword || filters.value.level))

const headerSubtitle = computed(() => {
  if (loading.value && logs.value.length === 0) return '正在读取日志'
  if (hasActiveFilters.value) {
    return `当前显示 ${logs.value.length.toLocaleString()} 条，共 ${totalLogs.value.toLocaleString()} 条`
  }
  return `共 ${totalLogs.value.toLocaleString()} 条记录`
})

const visibleCountLabel = computed(() => {
  return `${logs.value.length.toLocaleString()} / ${totalLogs.value.toLocaleString()} 条`
})

onMounted(() => {
  loadLogFiles()
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
  try {
    const params = {
      filename: filters.value.filename,
      keyword: filters.value.keyword || undefined,
      level: filters.value.level || undefined,
      page: 1,
      pageSize: 500,
    }
    const data = await queryLogs(params)
    if (data && requestId === latestRequestId) {
      logs.value = data.logs.map((log, index) => ({
        ...log,
        id: `${Date.now()}-${index}-${log.line_num}`,
      }))
      totalLogs.value = data.total
    }
  } catch (error) {
    Logger.error('Failed to load logs', error)
  } finally {
    if (requestId === latestRequestId) {
      loading.value = false
    }
  }
}

function applyKeywordFilter() {
  filters.value.keyword = keywordDraft.value.trim()
  loadLogs()
}

function clearFilters() {
  keywordDraft.value = ''
  filters.value.keyword = ''
  filters.value.level = ''
  loadLogs()
}

function filterByTraceId(traceId) {
  keywordDraft.value = traceId
  filters.value.keyword = traceId
  filters.value.level = ''
  loadLogs()
}

function updateKeywordDraft(value) {
  keywordDraft.value = value
  if (!value && filters.value.keyword) {
    filters.value.keyword = ''
    loadLogs()
  }
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

const { allCopied, copyLog, copyAllLogs } = useLogClipboard({ logs, filters })
const { autoRefresh, toggleAutoRefresh } = useLogAutoRefresh({ refresh: loadLogs })
</script>

<style scoped>
.log-viewer {
  --app-page-max-width: 2400px;
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
  padding-top: var(--space-4);
  padding-bottom: var(--space-4);
}

.log-toolbar {
  display: flex;
  width: 100%;
  min-width: 0;
  min-height: 2.5rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.log-toolbar__primary {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
}

.log-toolbar__search {
  max-width: 38rem;
}

.log-toolbar__actions {
  display: flex;
  min-width: 0;
  flex: none;
  align-items: center;
  gap: var(--space-2);
}

.log-toolbar__level {
  width: 7.5rem;
}

.log-toolbar__file {
  width: 13.5rem;
}

.log-toolbar__filter {
  gap: 0.4rem;
  color: hsl(var(--muted-foreground) / 0.84);
  font-size: 0.75rem;
}

.log-toolbar__filter.is-active {
  border-color: hsl(var(--foreground) / 0.1);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.82);
}

.log-toolbar__divider {
  flex: 0 0 auto;
  width: 1px;
  height: 1rem;
  background: var(--app-hairline);
}

.log-auto-refresh {
  display: inline-flex;
  min-height: 2rem;
  align-items: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.75rem;
  font-weight: 550;
  cursor: pointer;
}

.log-feed {
  --log-grid-columns: 7.5rem 4.75rem minmax(9rem, 13rem) minmax(18rem, 1fr) 2rem;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
}

.log-feed__header {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  padding: 0.25rem 0 var(--space-4);
}

.log-feed__identity {
  display: grid;
  min-width: 0;
  gap: 0.2rem;
}

.log-feed__title-row {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: var(--space-2);
}

.log-feed__title-row h2 {
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-feed__title-row span {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.7);
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.log-feed__identity p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.4;
}

.log-feed__state {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--space-3);
  color: hsl(var(--muted-foreground) / 0.76);
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.log-feed__divider {
  width: 1px;
  height: 0.875rem;
  background: var(--app-hairline);
}

.log-live-state {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.log-live-state__dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.4);
}

.log-live-state.is-active .log-live-state__dot {
  background: hsl(var(--primary));
  box-shadow: 0 0 0 0.1875rem hsl(var(--primary) / 0.1);
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
  border-top: 1px solid var(--app-hairline);
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--muted) / 0.14);
  padding: 0.4375rem 0.75rem;
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: 0.625rem;
  font-weight: 650;
}

.log-stream {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
  border-bottom: 1px solid var(--app-hairline);
  font-family: var(--font-mono);
}

.log-scroller {
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
}

.log-row {
  position: relative;
  min-height: 2.5rem;
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
  font-size: 0.6875rem;
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
  font-size: 0.625rem;
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
  border-color: hsl(var(--primary) / 0.24);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
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
  font-size: 0.6875rem;
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
  font-size: 0.75rem;
  line-height: 1.55;
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
  font-size: 0.625rem;
  line-height: 1.125rem;
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.log-trace:hover {
  border-color: hsl(var(--primary) / 0.26);
  background: hsl(var(--primary) / 0.06);
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

@media (max-width: 1320px) {
  .log-toolbar {
    flex-wrap: wrap;
    gap: var(--space-2) var(--space-4);
  }

  .log-toolbar__primary {
    flex-basis: 22rem;
  }

  .log-toolbar__search {
    max-width: none;
  }

  .log-toolbar__actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}

@media (max-width: 1100px) {
  .log-feed {
    --log-grid-columns: 7rem 4.5rem minmax(8rem, 10rem) minmax(16rem, 1fr) 2rem;
  }

  .log-toolbar__file {
    width: 11.5rem;
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
