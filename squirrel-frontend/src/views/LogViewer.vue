<template>
  <div class="log-viewer-container bg-bg-primary text-white min-h-screen p-3">
    <div class="max-w-7xl mx-auto">
      <!-- 顶部工具栏 -->
      <div class="flex justify-between items-center mb-3">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-bold">日志查看器</h1>
          <span class="text-xs text-gray-400">
            共 {{ totalLogs }} 条
            <span v-if="filters.keyword || filters.level" class="text-yellow-500">（已筛选）</span>
          </span>
        </div>
        <div class="flex gap-2">
          <button
            @click="copyAllLogs"
            :disabled="logs.length === 0"
            class="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors disabled:opacity-50 flex items-center gap-1"
            :title="'复制所有显示的日志 (' + logs.length + ' 条)'"
          >
            <ClipboardDocumentIcon class="h-4 w-4" />
            {{ allCopied ? '已复制全部' : '复制全部' }}
          </button>
          <button
            @click="toggleAutoRefresh"
            class="px-3 py-1.5 text-sm rounded transition-colors"
            :class="autoRefresh ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-700 hover:bg-gray-600'"
          >
            {{ autoRefresh ? '停止自动刷新' : '开启自动刷新' }}
          </button>
          <button
            @click="loadLogs"
            :disabled="loading"
            class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded transition-colors disabled:opacity-50"
          >
            {{ loading ? '加载中...' : '刷新' }}
          </button>
        </div>
      </div>

      <!-- 搜索和过滤区域 - 紧凑版 -->
      <div class="bg-bg-secondary border border-border-primary rounded-lg p-3 mb-3">
        <div class="flex flex-wrap gap-2 items-end">
          <!-- 搜索框 -->
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="filters.keyword"
              @keyup.enter="applyFilters"
              type="text"
              placeholder="搜索日志内容、trace_id..."
              class="w-full bg-bg-elevated border border-border-secondary rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <!-- 日志级别过滤 -->
          <div class="w-32">
            <select
              v-model="filters.level"
              @change="applyFilters"
              class="w-full bg-bg-elevated border border-border-secondary rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="">全部级别</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <!-- 日志文件选择 -->
          <div class="w-48">
            <select
              v-model="filters.filename"
              @change="applyFilters"
              class="w-full bg-bg-elevated border border-border-secondary rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
            >
              <option v-for="file in logFiles" :key="file.name" :value="file.name">
                {{ file.name }} ({{ formatFileSize(file.size) }})
              </option>
            </select>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-2">
            <button
              @click="clearFilters"
              class="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors whitespace-nowrap"
            >
              清空
            </button>
            <button
              @click="applyFilters"
              class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded transition-colors whitespace-nowrap"
            >
              应用
            </button>
          </div>
        </div>
      </div>

      <!-- 日志列表 -->
      <div class="bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
        <div v-if="loading && logs.length === 0" class="text-center py-8 text-sm text-gray-400">
          加载中...
        </div>

        <div v-else-if="logs.length === 0" class="text-center py-8 text-sm text-gray-400">
          暂无日志
        </div>

        <DynamicScroller
          v-else
          :items="logs"
          :min-item-size="60"
          key-field="id"
          class="scroller"
          :style="{ height: scrollerHeight }"
        >
          <template v-slot="{ item, index, active }">
            <DynamicScrollerItem
              :item="item"
              :active="active"
              :size-dependencies="[item.message]"
              :data-index="index"
            >
              <div
                class="log-entry border-b border-border-primary px-3 py-2 hover:bg-bg-elevated transition-colors group relative"
                :class="getLogLevelClass(item.level)"
              >
                <!-- 复制按钮 -->
                <button
                  @click="copyLog(item)"
                  class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white px-2 py-1 rounded text-[10px] flex items-center gap-1"
                  :title="'复制日志'"
                >
                  <ClipboardDocumentIcon class="h-3 w-3" />
                  <span v-if="copiedLogId === item.id" class="text-green-400">已复制</span>
                  <span v-else>复制</span>
                </button>

                <!-- 日志头部 -->
                <div class="flex items-center gap-2 mb-1 flex-wrap pr-16">
                  <span
                    class="log-level-badge px-1.5 py-0.5 rounded text-[10px] font-semibold leading-none"
                    :class="getLevelBadgeClass(item.level)"
                  >
                    {{ item.level }}
                  </span>
                  <span class="text-gray-400 text-xs">{{ item.timestamp }}</span>
                  <span 
                    v-if="item.trace_id" 
                    class="flex items-center gap-1"
                  >
                    <span
                      @click="filterByTraceId(item.trace_id)"
                      class="text-blue-400 text-[10px] font-mono bg-blue-950 px-1.5 py-0.5 rounded cursor-pointer hover:bg-blue-900 hover:text-blue-300 transition-colors" 
                      :title="'点击筛选 Trace ID: ' + item.trace_id"
                  >
                      {{ item.trace_id.substring(0, 8) }}
                    </span>
                  </span>
                  <span class="text-gray-500 text-xs">{{ item.logger }}</span>
                  <span class="text-gray-600 text-[10px] ml-auto">行 {{ item.line_num }}</span>
                </div>

                <!-- 日志内容 -->
                <div class="log-message font-mono text-xs whitespace-pre-wrap break-all ml-1 pl-2 border-l-2"
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
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller';
import { ClipboardDocumentIcon } from '@heroicons/vue/24/outline';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
import axios from '../utils/axios';

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

// 自动刷新定时器
let refreshTimer = null;
let copiedTimer = null;
let allCopiedTimer = null;

// 计算滚动器高度
const scrollerHeight = computed(() => {
  return 'calc(100vh - 200px)';
});

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
    const response = await axios.get('/api/logs/files');
    if (response.data.code === 0) {
      logFiles.value = response.data.data;
      if (logFiles.value.length > 0 && !filters.value.filename) {
        filters.value.filename = logFiles.value[0].name;
      }
    }
  } catch (error) {
    console.error('Failed to load log files:', error);
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
    
    const response = await axios.get('/api/logs/query', { params });
    
    if (response.data.code === 0) {
      const data = response.data.data;
      
      // 为每条日志添加唯一 ID
      const logsWithId = data.logs.map((log, index) => ({
        ...log,
        id: `${Date.now()}-${index}-${log.line_num}`
      }));
      
      logs.value = logsWithId;
      totalLogs.value = data.total;
    }
  } catch (error) {
    console.error('Failed to load logs:', error);
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
    console.error('复制失败:', err);
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
    console.error('复制失败:', err);
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
    DEBUG: 'bg-gray-600 text-gray-200',
    INFO: 'bg-blue-600 text-white',
    WARNING: 'bg-yellow-600 text-white',
    ERROR: 'bg-red-600 text-white',
    CRITICAL: 'bg-purple-600 text-white'
  };
  return classes[level] || 'bg-gray-600 text-gray-200';
}

function getLogLevelClass(level) {
  const classes = {
    ERROR: 'bg-red-900/10',
    CRITICAL: 'bg-purple-900/10',
    WARNING: 'bg-yellow-900/10'
  };
  return classes[level] || '';
}

function getMessageBorderClass(level) {
  const classes = {
    DEBUG: 'border-gray-600',
    INFO: 'border-blue-500',
    WARNING: 'border-yellow-500',
    ERROR: 'border-red-500',
    CRITICAL: 'border-purple-500'
  };
  return classes[level] || 'border-gray-600';
}
</script>

<style scoped>
.log-viewer-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.scroller {
  overflow-y: auto;
}

.scroller::-webkit-scrollbar {
  width: 8px;
}

.scroller::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.scroller::-webkit-scrollbar-thumb {
  background: #4a4a4a;
  border-radius: 4px;
}

.scroller::-webkit-scrollbar-thumb:hover {
  background: #5a5a5a;
}

.log-message {
  color: #e0e0e0;
}

.log-entry {
  cursor: default;
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

