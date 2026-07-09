<template>
  <AppPageShell class="log-viewer" variant="compact" fill>
    <AppToolbarFrame bordered compact sticky>
      <AppPaneHeader title="系统日志" :subtitle="headerSubtitle" :level="3">
        <template #actions>
          <span class="log-status-chip" :class="{ 'is-active': autoRefresh }">
            自动刷新 {{ autoRefresh ? '5s' : '关' }}
          </span>
          <Button
            size="sm"
            variant="outline"
            :disabled="logs.length === 0"
            :title="'复制所有显示的日志 (' + logs.length + ' 条)'"
            @click="copyAllLogs"
          >
            <AppIcon name="clipboard" class="h-4 w-4" />
            {{ allCopied ? '已复制全部' : '复制全部' }}
          </Button>
          <Button
            size="sm"
            :variant="autoRefresh ? 'secondary' : 'outline'"
            @click="toggleAutoRefresh"
          >
            {{ autoRefresh ? '停止自动刷新' : '开启自动刷新' }}
          </Button>
          <Button size="sm" :disabled="loading" @click="loadLogs">
            <AppSpinner v-if="loading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
            刷新
          </Button>
        </template>
      </AppPaneHeader>
    </AppToolbarFrame>

    <div class="app-page-content app-log-layout">
      <div class="app-log-filter-bar">
        <div class="log-filter-row">
          <AppSearchInput
            v-model="filters.keyword"
            class="log-filter-search"
            placeholder="搜索日志内容、追踪编号..."
            aria-label="搜索日志"
          />

          <Select :model-value="filters.level" @update:model-value="(value) => { filters.level = value; applyFilters() }">
            <SelectTrigger class="log-filter-select app-toolbar-select-trigger app-toolbar-control">
              <SelectValue placeholder="级别" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="option in levelOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>

          <Select :model-value="filters.filename" @update:model-value="(value) => { filters.filename = value; applyFilters() }">
            <SelectTrigger class="log-filter-select log-filter-select--file app-toolbar-select-trigger app-toolbar-control">
              <SelectValue placeholder="日志文件" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="option in fileOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>

          <Button size="sm" variant="ghost" @click="clearFilters">清空</Button>
          <Button size="sm" variant="secondary" @click="applyFilters">应用</Button>
        </div>
      </div>

      <div class="app-log-stream app-surface app-surface--subtle">
        <div v-if="loading && logs.length === 0" class="log-loading">
          <AppSpinner size="sm" />
          <span>加载中...</span>
        </div>

        <AppEmptyState
          v-else-if="logs.length === 0"
          class="log-empty-state"
          variant="plain"
          icon="inbox"
          :title="hasActiveFilters ? '没有匹配的日志' : '暂无日志'"
          :copy="hasActiveFilters ? '调整搜索条件后再试。' : '当前日志文件里还没有内容。'"
        >
          <template #actions>
            <Button v-if="hasActiveFilters" size="sm" variant="secondary" @click="clearFilters">清空筛选</Button>
            <Button size="sm" @click="loadLogs">刷新</Button>
          </template>
        </AppEmptyState>

        <DynamicScroller
          v-else
          :items="logs"
          :min-item-size="28"
          key-field="id"
          class="scroller flex-1 min-h-0 custom-scrollbar"
        >
          <template v-slot="{ item, index, active }">
            <DynamicScrollerItem
              :item="item"
              :active="active"
              :size-dependencies="[item.message]"
              :data-index="index"
            >
              <div class="app-log-row group">
                <span class="log-time">
                  {{ formatLogTimestamp(item.timestamp) }}
                </span>

                <span class="log-level" :class="getLevelColorClass(item.level)">
                  {{ item.level }}
                </span>

                <div class="log-body">
                  <div class="log-meta">
                    <button
                      v-if="item.trace_id"
                      type="button"
                      class="log-trace"
                      @click="filterByTraceId(item.trace_id)"
                    >
                      {{ item.trace_id.substring(0, 8) }}
                    </button>
                    <span>{{ item.logger }}</span>
                    <span>:{{ item.line_num }}</span>
                  </div>
                  <div class="log-message">{{ item.message }}</div>
                </div>

                <div class="log-row-actions">
                  <Button
                    size="xs"
                    variant="ghost"
                    class="h-6 w-6 p-0"
                    title="复制日志"
                    aria-label="复制日志"
                    @click="copyLog(item)"
                  >
                    <AppIcon name="clipboard" class="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </DynamicScrollerItem>
          </template>
        </DynamicScroller>
      </div>
    </div>
  </AppPageShell>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppPaneHeader from '@/shared/components/layout/AppPaneHeader.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import { Button } from '@/shared/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { getLogFiles, queryLogs } from '@/shared/api'
import { Logger } from '@/shared/lib/logger'
import { useLogClipboard } from '@/features/settings/composables/useLogClipboard'
import { useLogAutoRefresh } from '@/features/settings/composables/useLogAutoRefresh'
import { formatLogTimestamp, getLevelColorClass, formatFileSize } from '@/features/settings/lib/logPresenters'

const logs = ref([])
const logFiles = ref([])
const totalLogs = ref(0)
const loading = ref(false)

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
    label: `${file.name} (${formatFileSize(file.size)})`,
  }))
})

const hasActiveFilters = computed(() => Boolean(filters.value.keyword || filters.value.level))
const headerSubtitle = computed(() => {
  const total = `共 ${totalLogs.value} 条`
  return hasActiveFilters.value ? `${total} · 已筛选` : total
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
  if (loading.value) return
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
    if (data) {
      logs.value = data.logs.map((log, index) => ({
        ...log,
        id: `${Date.now()}-${index}-${log.line_num}`,
      }))
      totalLogs.value = data.total
    }
  } catch (error) {
    Logger.error('Failed to load logs', error)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  loadLogs()
}

function clearFilters() {
  filters.value.keyword = ''
  filters.value.level = ''
  applyFilters()
}

function filterByTraceId(traceId) {
  filters.value.keyword = traceId
  filters.value.level = ''
  applyFilters()
}

const { allCopied, copyLog, copyAllLogs } = useLogClipboard({ logs, filters })
const { autoRefresh, toggleAutoRefresh } = useLogAutoRefresh({ refresh: loadLogs })
</script>

<style scoped>
.log-viewer {
  min-height: 0;
}

.log-status-chip {
  display: inline-flex;
  min-height: 1.75rem;
  align-items: center;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.4);
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.log-status-chip.is-active {
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--foreground));
}

.log-filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.log-filter-search {
  flex: 1 1 15rem;
  min-width: 12rem;
}

.log-filter-select {
  width: 7.5rem;
}

.log-filter-select--file {
  width: 11rem;
}

.log-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 5rem 1rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
}

.log-empty-state {
  min-height: 18rem;
}

.log-time {
  flex: none;
  padding-top: 0.125rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.log-level {
  width: 4rem;
  flex: none;
  padding-top: 0.125rem;
  font-size: 0.75rem;
  font-weight: 650;
  line-height: 1.2;
}

.log-body {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.125rem;
}

.log-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.6);
  font-size: 0.75rem;
}

.log-trace {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-decoration: underline;
  text-decoration-style: dotted;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
}

.log-trace:hover {
  color: hsl(var(--foreground));
}

.log-message {
  color: hsl(var(--foreground) / 0.9);
  font-size: 0.8125rem;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.log-row-actions {
  position: absolute;
  top: 0.25rem;
  right: 0.5rem;
  display: flex;
  gap: 0.125rem;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  background: hsl(var(--background));
  padding: 0.125rem;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-default);
}

.group:hover .log-row-actions,
.group:focus-within .log-row-actions {
  opacity: 1;
}

.scroller {
  overflow-y: auto;
}

@media (prefers-reduced-motion: reduce) {
  .log-trace,
  .log-row-actions {
    transition: none;
  }
}
</style>
