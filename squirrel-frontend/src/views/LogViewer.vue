<template>
  <div class="log-viewer-container bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-4 pb-4">
      <PageHeader
        title="日志查看器"
        description="把错误、链路和上下文折叠成连续的排障时间线，适合快速筛选 trace、定位异常和导出现场。"
      >
        <template #actions>
          <div class="log-hero__pill">
            <span class="log-hero__label">总量</span>
            <span>共 {{ totalLogs }} 条</span>
            <span v-if="hasActiveFilters" class="text-warning">已筛选</span>
          </div>
          <div class="log-hero__pill">
            <span class="log-hero__label">自动刷新</span>
            <span>{{ autoRefresh ? '5s' : '关闭' }}</span>
          </div>
          <Button
            @click="copyAllLogs"
            :disabled="logs.length === 0"
            size="sm"
            variant="outline"
            class="log-toolbar-button"
            :title="'复制所有显示的日志 (' + logs.length + ' 条)'"
          >
            <ClipboardDocumentIcon class="h-4 w-4" />
            {{ allCopied ? '已复制全部' : '复制全部' }}
          </Button>
          <Button
            @click="toggleAutoRefresh"
            size="sm"
            :variant="autoRefresh ? 'secondary' : 'outline'"
            class="log-toolbar-button"
          >
            {{ autoRefresh ? '停止自动刷新' : '开启自动刷新' }}
          </Button>
          <Button
            @click="loadLogs"
            :disabled="loading"
            size="sm"
            class="log-toolbar-button"
          >
            <span
              v-if="loading"
              class="h-3 w-3 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"
            ></span>
            <span>刷新</span>
          </Button>
        </template>
      </PageHeader>
    </div>

    <div class="content-container py-5 space-y-4 flex-1 flex flex-col min-h-0 overflow-hidden">
      <div class="log-filter-shell">
        <div class="flex flex-wrap gap-3 items-end">
          <div class="flex-1 min-w-[200px]">
            <Input
              v-model="filters.keyword"
              @keyup.enter="applyFilters"
              type="text"
              placeholder="搜索日志内容、trace_id..."
              class="log-search-input"
            />
          </div>

          <div class="w-32">
            <Select :model-value="filters.level" @update:model-value="(value) => { filters.level = value; applyFilters(); }">
              <SelectTrigger class="h-8 text-xs border-border/80 bg-background/80">
                <SelectValue placeholder="级别" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in levelOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-48">
            <Select :model-value="filters.filename" @update:model-value="(value) => { filters.filename = value; applyFilters(); }">
              <SelectTrigger class="h-8 text-xs border-border/80 bg-background/80">
                <SelectValue placeholder="日志文件" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in fileOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="flex gap-2">
            <Button
              @click="clearFilters"
              size="sm"
              variant="outline"
              class="log-toolbar-button"
            >
              清空
            </Button>
            <Button
              @click="applyFilters"
              size="sm"
              class="log-toolbar-button"
            >
              应用
            </Button>
          </div>
        </div>
      </div>

      <div class="log-stream-shell overflow-hidden flex flex-col min-h-0 flex-1">

        <div v-if="loading && logs.length === 0" class="text-center py-8 text-sm text-muted-foreground">
          加载中...
        </div>

        <div v-else-if="logs.length === 0" class="text-center py-8 text-sm text-muted-foreground">
          暂无日志
        </div>

        <DynamicScroller
          v-else
          :items="logs"
          :min-item-size="60"
          key-field="id"
          class="scroller flex-1 min-h-0"
        >
          <template v-slot="{ item, index, active }">
            <DynamicScrollerItem
              :item="item"
              :active="active"
              :size-dependencies="[item.message]"
              :data-index="index"
            >
              <div
                class="log-entry border-b border-border px-3 py-3 group relative"
                :class="getLogLevelClass(item.level)"
              >
                <Button
                  @click="copyLog(item)"
                  size="xs"
                  variant="outline"
                  class="log-copy-button"
                  :title="'复制日志'"
                >
                  <ClipboardDocumentIcon class="h-3 w-3" />
                  <span v-if="copiedLogId === item.id" class="text-success">已复制</span>
                  <span v-else>复制</span>
                </Button>

                <div class="flex items-center gap-2 mb-1 flex-wrap pr-16">
                  <span
                    class="log-level-badge"
                    :class="getLevelBadgeClass(item.level)"
                  >
                    {{ item.level }}
                  </span>

                  <span class="text-muted-foreground text-xs">{{ item.timestamp }}</span>
                  <span 
                    v-if="item.trace_id" 
                    class="flex items-center gap-1"
                  >
                    <span
                      @click="filterByTraceId(item.trace_id)"
                      class="log-trace-chip" 
                      :title="'点击筛选 Trace ID: ' + item.trace_id"
                  >
                      {{ item.trace_id.substring(0, 8) }}
                    </span>
                  </span>
                  <span class="text-muted-foreground text-xs">{{ item.logger }}</span>
                  <span class="text-muted-foreground text-2xs ml-auto">行 {{ item.line_num }}</span>
                </div>

                <div class="log-message font-mono text-xs whitespace-pre-wrap break-all ml-1 pl-3 border-l-2"
                     :class="getMessageBorderClass(item.level)">
                  {{ item.message }}
                </div>
              </div>
            </DynamicScrollerItem>
          </template>
        </DynamicScroller>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller';
import { ClipboardDocumentIcon } from '@heroicons/vue/24/outline';
import PageHeader from '@/components/layout/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
import { getLogFiles, queryLogs } from '@/api'
import { Logger } from '@/utils/logger'


// 数据
const logs = ref([]);
const logFiles = ref([]);
const totalLogs = ref(0);
const loading = ref(false);
const autoRefresh = ref(true);
const copiedLogId = ref(null);
const allCopied = ref(false);

// 过滤条件
const filters = ref({
  keyword: '',
  level: '',
  filename: 'app.log'
});

const levelOptions = [
  { value: '', label: '全部级别' },
  { value: 'DEBUG', label: 'DEBUG' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
  { value: 'CRITICAL', label: 'CRITICAL' }
];

const fileOptions = computed(() => {
  return logFiles.value.map((file) => ({
    value: file.name,
    label: `${file.name} (${formatFileSize(file.size)})`
  }));
});

const hasActiveFilters = computed(() => Boolean(filters.value.keyword || filters.value.level))


// 自动刷新定时器
let refreshTimer = null;
let copiedTimer = null;
let allCopiedTimer = null;

// 生命周期
onMounted(() => {
  loadLogFiles();
  loadLogs();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});

// 加载日志文件列表
async function loadLogFiles() {
  try {
    const { data, error } = await getLogFiles()
    if (error) {
      Logger.error('Failed to load log files', error);
      return
    }

    logFiles.value = data || []
    if (logFiles.value.length > 0 && !filters.value.filename) {
      filters.value.filename = logFiles.value[0].name;
    }
  } catch (error) {
    Logger.error('Failed to load log files', error);
  }
}

// 加载日志
async function loadLogs() {
  if (loading.value) return;
  
  loading.value = true;
  
  try {
    const params = {
      filename: filters.value.filename,
      keyword: filters.value.keyword || undefined,
      level: filters.value.level || undefined,
      page: 1,
      pageSize: 500
    };
    
    const result = await queryLogs(params)
    if (!result.error && result.data) {
      const data = result.data;
      
      // 为每条日志添加唯一 ID
      const logsWithId = data.logs.map((log, index) => ({
        ...log,
        id: `${Date.now()}-${index}-${log.line_num}`
      }));
      
      logs.value = logsWithId;
      totalLogs.value = data.total;
    }
  } catch (error) {
    Logger.error('Failed to load logs', error);
  } finally {
    loading.value = false;
  }
}

// 应用筛选
function applyFilters() {
  loadLogs();
}

// 清空筛选
function clearFilters() {
  filters.value.keyword = '';
  filters.value.level = '';
  applyFilters();
}

// 按 trace_id 筛选
function filterByTraceId(traceId) {
  filters.value.keyword = traceId;
  filters.value.level = '';
  applyFilters();
}

// 复制单条日志
function copyLog(logItem) {
  // 构建完整的日志文本
  let logText = '';
  
  // 添加日志元信息
  logText += `时间: ${logItem.timestamp}\n`;
  if (logItem.trace_id) {
    logText += `Trace ID: ${logItem.trace_id}\n`;
  }
  logText += `级别: ${logItem.level}\n`;
  logText += `日志器: ${logItem.logger}\n`;
  logText += `行号: ${logItem.line_num}\n`;
  logText += `\n内容:\n${logItem.message}\n`;
  
  // 复制到剪贴板
  navigator.clipboard.writeText(logText).then(() => {
    // 显示复制成功状态
    copiedLogId.value = logItem.id;
    
    // 清除之前的定时器
    if (copiedTimer) {
      clearTimeout(copiedTimer);
    }
    
    // 2秒后清除复制状态
    copiedTimer = setTimeout(() => {
      copiedLogId.value = null;
    }, 2000);
  }).catch(err => {
    Logger.error('Failed to copy log', err);
    alert('复制失败，请手动复制');
  });
}

// 复制所有日志
function copyAllLogs() {
  if (logs.value.length === 0) {
    return;
  }
  
  // 构建所有日志的文本
  let allLogsText = `日志导出 - 共 ${logs.value.length} 条\n`;
  allLogsText += `文件: ${filters.value.filename}\n`;
  if (filters.value.keyword) {
    allLogsText += `搜索: ${filters.value.keyword}\n`;
  }
  if (filters.value.level) {
    allLogsText += `级别: ${filters.value.level}\n`;
  }
  allLogsText += `导出时间: ${new Date().toLocaleString()}\n`;
  allLogsText += `${'='.repeat(80)}\n\n`;
  
  logs.value.forEach((logItem, index) => {
    allLogsText += `[${index + 1}] `;
    allLogsText += `${logItem.timestamp} `;
    if (logItem.trace_id) {
      allLogsText += `[${logItem.trace_id}] `;
    }
    allLogsText += `${logItem.level} `;
    allLogsText += `${logItem.logger}: `;
    allLogsText += `${logItem.message}\n`;
    allLogsText += `${'-'.repeat(80)}\n`;
  });
  
  // 复制到剪贴板
  navigator.clipboard.writeText(allLogsText).then(() => {
    // 显示复制成功状态
    allCopied.value = true;
    
    // 清除之前的定时器
    if (allCopiedTimer) {
      clearTimeout(allCopiedTimer);
    }
    
    // 2秒后清除复制状态
    allCopiedTimer = setTimeout(() => {
      allCopied.value = false;
    }, 2000);
  }).catch(err => {
    Logger.error('Failed to copy logs', err);
    alert('复制失败，请手动复制');
  });
}

// 切换自动刷新
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value;
  
  if (autoRefresh.value) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
}

// 开始自动刷新
function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(() => {
    loadLogs();
  }, 5000);
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

// 获取日志级别样式
function getLevelBadgeClass(level) {
  const classes = {
    DEBUG: 'log-level-badge--debug',
    INFO: 'log-level-badge--info',
    WARNING: 'log-level-badge--warning',
    ERROR: 'log-level-badge--error',
    CRITICAL: 'log-level-badge--critical'
  };
  return classes[level] || 'log-level-badge--debug';
}

function getLogLevelClass(level) {
  const classes = {
    DEBUG: 'log-entry--debug',
    INFO: 'log-entry--info',
    WARNING: 'log-entry--warning',
    ERROR: 'log-entry--error',
    CRITICAL: 'log-entry--critical'
  };
  return classes[level] || 'log-entry--debug';
}

function getMessageBorderClass(level) {
  const classes = {
    DEBUG: 'border-border',
    INFO: 'border-info/40',
    WARNING: 'border-warning/45',
    ERROR: 'border-destructive/60',
    CRITICAL: 'border-destructive'
  };
  return classes[level] || 'border-border';
}
</script>

<style scoped>
.toolbar-container,
.content-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding-left: 1rem;
  padding-right: 1rem;
  width: 100%;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

.log-viewer-container {
  font-family: var(--font-sans);
}

.log-filter-shell,
.log-stream-shell {
  border: 1px solid hsl(var(--border) / 0.76);
  background: linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.035);
}

.log-hero__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: hsl(var(--muted-foreground));
}

.log-hero__pill,
.log-toolbar-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2rem;
  padding: 0.45rem 0.75rem;
  border-radius: 0.625rem;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  transition: background-color 160ms ease, opacity 160ms ease;
}

.log-toolbar-button:hover:not(:disabled) {
  background: hsl(var(--accent));
}

.log-toolbar-button:disabled {
  opacity: 0.5;
}

.log-filter-shell {
  padding: 0.9rem;
  border-radius: 0.875rem;
}

.log-search-input::placeholder {
  color: hsl(var(--muted-foreground));
}

.log-stream-shell {
  border-radius: 0.875rem;
}

.scroller {
  overflow-y: auto;
}

.scroller::-webkit-scrollbar {
  width: 8px;
}

.scroller::-webkit-scrollbar-track {
  background: hsl(var(--card));
}

.scroller::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 4px;
}

.scroller::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

.log-message {
  color: hsl(var(--foreground));
  line-height: 1.65;
}

.log-entry {
  cursor: default;
  transition: background-color 160ms ease;
}

.log-entry--debug:hover,
.log-entry--info:hover,
.log-entry--warning:hover,
.log-entry--error:hover,
.log-entry--critical:hover {
  background-color: hsl(var(--accent) / 0.55);
}

.log-entry--debug {
  background: transparent;
}

.log-entry--info {
  background: hsl(var(--info) / 0.06);
}

.log-entry--warning {
  background: hsl(var(--warning) / 0.08);
}

.log-entry--error {
  background: hsl(var(--destructive) / 0.08);
}

.log-entry--critical {
  background: hsl(var(--destructive) / 0.12);
}

.log-copy-button {
  position: absolute;
  top: 0.65rem;
  right: 0.65rem;
  opacity: 0;
  transition: opacity 160ms ease;
}

.group:hover .log-copy-button {
  opacity: 1;
}

.log-level-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  border: 1px solid transparent;
}

.log-level-badge--debug {
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted));
  border-color: hsl(var(--border));
}

.log-level-badge--info {
  color: hsl(var(--info));
  background: hsl(var(--info) / 0.12);
  border-color: hsl(var(--info) / 0.2);
}

.log-level-badge--warning {
  color: hsl(var(--warning));
  background: hsl(var(--warning) / 0.12);
  border-color: hsl(var(--warning) / 0.2);
}

.log-level-badge--error,
.log-level-badge--critical {
  color: hsl(var(--destructive));
  background: hsl(var(--destructive) / 0.12);
  border-color: hsl(var(--destructive) / 0.24);
}

.log-trace-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.55rem;
  border-radius: 0.625rem;
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
  font-size: 0.68rem;
  font-family: var(--font-mono, monospace);
  cursor: pointer;
  transition: background-color 160ms ease, color 160ms ease;
}

.log-trace-chip:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

select,
input[type="text"] {
  appearance: none;
  -webkit-appearance: none;
}

select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}
</style>

