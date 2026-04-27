<template>
  <AppPageShell class="log-viewer-container">
    <AppToolbarFrame class="toolbar-container" compact>
      <div class="flex flex-wrap items-center justify-end gap-2">
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
          <AppIcon name="clipboard" class="h-4 w-4" />
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
      </div>
    </AppToolbarFrame>

    <div class="content-container py-2 space-y-2 flex-1 flex flex-col min-h-0 overflow-hidden">
      <div class="log-filter-area border-b border-border/40 pb-4">
        <div class="flex flex-wrap gap-2 items-center">
          <div class="flex-1 min-w-[240px]">
            <Input
              v-model="filters.keyword"
              @keyup.enter="applyFilters"
              type="text"
              placeholder="搜索日志内容、trace_id..."
              class="h-8 text-xs bg-muted/30 border-none focus-visible:ring-1"
            />
          </div>

          <div class="w-28">
            <Select :model-value="filters.level" @update:model-value="(value) => { filters.level = value; applyFilters(); }">
              <SelectTrigger class="h-8 text-xs border-none bg-muted/30">
                <SelectValue placeholder="级别" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in levelOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-40">
            <Select :model-value="filters.filename" @update:model-value="(value) => { filters.filename = value; applyFilters(); }">
              <SelectTrigger class="h-8 text-xs border-none bg-muted/30">
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
              variant="ghost"
              class="h-8 px-3 text-xs"
            >
              清空
            </Button>
            <Button
              @click="applyFilters"
              size="sm"
              variant="secondary"
              class="h-8 px-3 text-xs"
            >
              应用
            </Button>
          </div>
        </div>
      </div>

      <div class="log-stream-container flex-1 flex flex-col min-h-0 overflow-hidden font-mono text-[13px]">
        <div v-if="loading && logs.length === 0" class="flex items-center justify-center py-20 text-muted-foreground">
          <span class="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground mr-2"></span>
          加载中...
        </div>

        <AppEmptyState
          v-else-if="logs.length === 0"
          class="log-empty-state"
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
                class="log-row border-b border-border/20 py-1 px-2 group hover:bg-muted/30 transition-colors flex items-start gap-3 relative"
              >
                <!-- Time -->
                <span class="text-muted-foreground/60 whitespace-nowrap tabular-nums shrink-0 pt-0.5">
                  {{ formatTime(item.timestamp) }}
                </span>

                <!-- Level -->
                <span 
                  class="w-16 shrink-0 uppercase font-bold text-[11px] pt-0.5"
                  :class="getLevelColorClass(item.level)"
                >
                  {{ item.level }}
                </span>

                <!-- Content Area -->
                <div class="flex-1 min-w-0 flex flex-col gap-0.5">
                  <!-- Meta -->
                  <div class="flex items-center gap-3 text-[11px] text-muted-foreground/50">
                    <span v-if="item.trace_id" 
                          @click="filterByTraceId(item.trace_id)"
                          class="hover:text-foreground cursor-pointer underline decoration-dotted transition-colors">
                      {{ item.trace_id.substring(0, 8) }}
                    </span>
                    <span>{{ item.logger }}</span>
                    <span>:{{ item.line_num }}</span>
                  </div>

                  <!-- Message -->
                  <div class="log-message whitespace-pre-wrap break-all leading-relaxed">
                    {{ item.message }}
                  </div>
                </div>

                <!-- Actions -->
                <div class="opacity-0 group-hover:opacity-100 absolute right-2 top-1 flex gap-1 bg-background/80 backdrop-blur-sm rounded border border-border/40 p-0.5">
                  <Button
                    @click="copyLog(item)"
                    size="xs"
                    variant="ghost"
                    class="h-6 w-6 p-0"
                    title="复制日志"
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
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller';
import AppIcon from '@/components/common/AppIcon.vue';
import AppEmptyState from '@/components/layout/AppEmptyState.vue';
import AppPageShell from '@/components/layout/AppPageShell.vue';
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue';
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

// 格式化时间
function formatTime(timestamp) {
  if (!timestamp) return '';
  const parts = timestamp.split(' ');
  if (parts.length > 1) {
    return parts[1];
  }
  return timestamp;
}

// 获取日志级别颜色
function getLevelColorClass(level) {
  const classes = {
    DEBUG: 'text-muted-foreground/40',
    INFO: 'text-info/80',
    WARNING: 'text-warning/80',
    ERROR: 'text-destructive',
    CRITICAL: 'text-destructive font-black'
  };
  return classes[level] || 'text-muted-foreground';
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}
</script>

<style scoped>
.content-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding-left: var(--app-page-gutter);
  padding-right: var(--app-page-gutter);
  width: 100%;
}

@media (min-width: 640px) {
  .content-container {
    padding-left: var(--app-page-gutter-sm);
    padding-right: var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .content-container {
    padding-left: var(--app-page-gutter-lg);
    padding-right: var(--app-page-gutter-lg);
  }
}

.log-hero__label {
  font-size: 0.68rem;
  color: hsl(var(--muted-foreground));
}

.log-hero__pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 1.75rem;
  padding: 0 0.75rem;
  border-radius: var(--app-control-item-radius);
  background: hsl(var(--muted) / 0.5);
  font-size: 0.75rem;
}

.log-empty-state {
  min-height: 18rem;
}

.log-toolbar-button {
  height: 1.75rem;
  font-size: 0.75rem;
  padding: 0 0.75rem;
}

.scroller {
  overflow-y: auto;
}

/* 隐藏滚动条背景 */
.scroller::-webkit-scrollbar {
  width: 6px;
}

.scroller::-webkit-scrollbar-thumb {
  background: hsl(var(--border));
  border-radius: 3px;
}

.scroller::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.4);
}

.log-message {
  color: hsl(var(--foreground));
}
</style>
