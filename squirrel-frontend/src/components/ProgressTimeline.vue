<template>
  <div class="progress-timeline">
    <!-- 头部 -->
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-white">
        视频提取队列
      </h3>
      <button 
        @click="refreshTimeline"
        :disabled="loading"
        class="btn-refresh"
      >
        <svg 
          class="w-4 h-4" 
          :class="{ 'animate-spin': loading }"
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span class="ml-1">刷新</span>
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && allVideos.length === 0" class="text-center py-8">
      <div class="spinner mx-auto mb-2"></div>
      <p class="text-[#aaa] text-sm">加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && allVideos.length === 0" class="text-center py-8">
      <svg class="w-12 h-12 mx-auto text-[#666] mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
      <p class="text-[#aaa] text-sm">队列为空</p>
    </div>

    <!-- 队列视图 -->
    <div v-else class="queue-view">
      <!-- 队列统计 -->
      <div class="queue-stats">
        <div class="stat-item">
          <div class="stat-label">队列总数</div>
          <div class="stat-value">{{ videoStats.total }}</div>
        </div>
        <div class="stat-divider">→</div>
        <div class="stat-item stat-item-processing">
          <div class="stat-label">处理中</div>
          <div class="stat-value">{{ videoStats.processing }}</div>
        </div>
        <div class="stat-divider">→</div>
        <div class="stat-item stat-item-completed">
          <div class="stat-label">已完成</div>
          <div class="stat-value">{{ videoStats.completed }}</div>
        </div>
        <div class="stat-divider">×</div>
        <div class="stat-item stat-item-failed">
          <div class="stat-label">失败</div>
          <div class="stat-value">{{ videoStats.failed }}</div>
        </div>
      </div>

      <!-- 三段式队列 -->
      <div class="queue-container">
        <!-- 正在处理 -->
        <div class="queue-section queue-section-processing">
          <div class="queue-section-header">
            <div class="section-icon">
              <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <div class="section-title">正在处理</div>
            <div class="section-count">{{ processingVideos.length }}</div>
          </div>
          
          <div class="queue-items" v-if="processingVideos.length > 0">
            <div 
              v-for="(video, index) in processingVideos" 
              :key="index"
              class="queue-item queue-item-processing"
              :class="{ 'queue-item-active': index === 0 }"
            >
              <div class="item-indicator">
                <div class="indicator-dot"></div>
                <div v-if="index === 0" class="indicator-label">当前</div>
                <div v-else class="indicator-label">等待</div>
              </div>
              
              <div class="item-content">
                <div class="item-header">
                  <div class="item-title" :title="getVideoTitle(video.url)">
                    {{ getVideoTitle(video.url) }}
                  </div>
                  <div class="item-time">{{ formatTime(video.time) }}</div>
                </div>
                
                <div class="item-meta">
                  <span class="meta-tag">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    {{ getSubscriptionName(video.subscription_id) || `订阅 #${video.subscription_id}` }}
                  </span>
                </div>
                
                <div class="item-message">{{ video.message }}</div>
                
                <a :href="video.url" target="_blank" class="item-url">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  <span class="url-text">{{ video.url }}</span>
                </a>
              </div>
            </div>
          </div>
          
          <div v-else class="queue-empty">
            <svg class="w-8 h-8 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p class="text-xs text-[#666] mt-2">暂无处理中的视频</p>
          </div>
        </div>

        <!-- 流向箭头 -->
        <div class="queue-flow-arrow">
          <svg class="w-8 h-8 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </div>

        <!-- 已完成 -->
        <div class="queue-section queue-section-completed">
          <div class="queue-section-header">
            <div class="section-icon section-icon-success">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div class="section-title">已完成</div>
            <div class="section-count">{{ completedVideos.length }}</div>
          </div>
          
          <div class="queue-items scrollable" v-if="completedVideos.length > 0">
            <div 
              v-for="(video, index) in completedVideos" 
              :key="index"
              class="queue-item queue-item-completed"
            >
              <div class="item-indicator">
                <div class="indicator-dot"></div>
              </div>
              
              <div class="item-content">
                <div class="item-header">
                  <div class="item-title" :title="getVideoTitle(video.url)">
                    {{ getVideoTitle(video.url) }}
                  </div>
                  <div class="item-time">{{ formatTime(video.time) }}</div>
                </div>
                
                <div class="item-meta">
                  <span class="meta-tag">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    {{ getSubscriptionName(video.subscription_id) || `订阅 #${video.subscription_id}` }}
                  </span>
                </div>
                
                <div class="item-message">{{ video.message }}</div>
              </div>
            </div>
          </div>
          
          <div v-else class="queue-empty">
            <svg class="w-8 h-8 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-xs text-[#666] mt-2">暂无完成的视频</p>
          </div>
        </div>

        <!-- 流向箭头（失败） -->
        <div class="queue-flow-arrow queue-flow-arrow-error">
          <svg class="w-8 h-8 text-[#f87171]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17l5-5m0 0l-5-5m5 5H6" />
          </svg>
          <div class="flow-label">异常</div>
        </div>

        <!-- 失败 -->
        <div class="queue-section queue-section-failed">
          <div class="queue-section-header">
            <div class="section-icon section-icon-error">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div class="section-title">失败</div>
            <div class="section-count">{{ failedVideos.length }}</div>
          </div>
          
          <div class="queue-items scrollable" v-if="failedVideos.length > 0">
            <div 
              v-for="(video, index) in failedVideos" 
              :key="index"
              class="queue-item queue-item-failed"
            >
              <div class="item-indicator">
                <div class="indicator-dot"></div>
              </div>
              
              <div class="item-content">
                <div class="item-header">
                  <div class="item-title" :title="getVideoTitle(video.url)">
                    {{ getVideoTitle(video.url) }}
                  </div>
                  <div class="item-time">{{ formatTime(video.time) }}</div>
                </div>
                
                <div class="item-meta">
                  <span class="meta-tag">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    {{ getSubscriptionName(video.subscription_id) || `订阅 #${video.subscription_id}` }}
                  </span>
                </div>
                
                <div v-if="video.error" class="item-error">
                  <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <span>{{ video.error }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div v-else class="queue-empty">
            <svg class="w-8 h-8 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-xs text-[#666] mt-2">暂无失败的视频</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useProgressApi } from '../composables/useProgressApi';

const props = defineProps({
  subscriptionId: {
    type: Number,
    default: null
  },
  traceId: {
    type: String,
    default: null
  },
  autoRefresh: {
    type: Boolean,
    default: false
  },
  refreshInterval: {
    type: Number,
    default: 5000
  }
});

const { getProgressTimeline } = useProgressApi();

const loading = ref(false);
const timeline = ref([]);
let refreshTimer = null;

const subscriptionNames = ref(new Map());

const loadTimeline = async () => {
  loading.value = true;
  try {
    const params = {
      all: true
    };
    
    if (props.subscriptionId) {
      params.subscriptionId = props.subscriptionId;
    }
    if (props.traceId) {
      params.traceId = props.traceId;
    }
    
    const result = await getProgressTimeline(params);
    if (result.success && result.data) {
      timeline.value = result.data;
    }
  } finally {
    loading.value = false;
  }
};

const refreshTimeline = () => {
  loadTimeline();
};

// 从时间线提取所有视频
const allVideos = computed(() => {
  const videoMap = new Map();
  
  for (const item of timeline.value) {
    const eventType = item.event_type;
    
    if (eventType.startsWith('video_extraction_')) {
      const url = item.url;
      if (!url) continue;
      
      if (!videoMap.has(url)) {
        videoMap.set(url, {
          url: url,
          status: 'progress',
          message: '',
          error: null,
          time: item.created_at,
          subscription_id: item.subscription_id
        });
      }
      
      const video = videoMap.get(url);
      
      if (eventType === 'video_extraction_start') {
        video.status = 'progress';
        video.message = item.message || '开始提取';
        video.time = item.created_at;
      } else if (eventType === 'video_extraction_complete') {
        video.status = 'success';
        video.message = item.message || '提取完成';
        video.time = item.created_at;
      } else if (eventType === 'video_extraction_error') {
        video.status = 'error';
        video.message = '提取失败';
        video.error = item.error_message || item.message;
        video.time = item.created_at;
      }
    }
  }
  
  return Array.from(videoMap.values()).sort((a, b) => new Date(b.time) - new Date(a.time));
});

// 按状态分类
const processingVideos = computed(() => 
  allVideos.value.filter(v => v.status === 'progress').sort((a, b) => new Date(a.time) - new Date(b.time))
);

const completedVideos = computed(() => 
  allVideos.value.filter(v => v.status === 'success').sort((a, b) => new Date(b.time) - new Date(a.time)).slice(0, 10)
);

const failedVideos = computed(() => 
  allVideos.value.filter(v => v.status === 'error').sort((a, b) => new Date(b.time) - new Date(a.time)).slice(0, 10)
);

// 统计数据
const videoStats = computed(() => ({
  total: allVideos.value.length,
  processing: processingVideos.value.length,
  completed: allVideos.value.filter(v => v.status === 'success').length,
  failed: allVideos.value.filter(v => v.status === 'error').length
}));

// 获取视频标题
const getVideoTitle = (url) => {
  if (!url) return '未知视频';
  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname;
    const lastSegment = pathname.split('/').filter(Boolean).pop();
    return lastSegment || urlObj.hostname;
  } catch {
    return url.split('/').pop() || url;
  }
};

// 获取订阅名称
const getSubscriptionName = (subscriptionId) => {
  return subscriptionNames.value.get(subscriptionId);
};

// 格式化时间
const formatTime = (time) => {
  if (!time) return '';
  try {
    const date = new Date(time);
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) return `${seconds}秒前`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}分钟前`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}小时前`;
    
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return time;
  }
};

onMounted(() => {
  loadTimeline();
  
  if (props.autoRefresh) {
    refreshTimer = setInterval(loadTimeline, props.refreshInterval);
  }
});

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
});

watch(() => [props.subscriptionId, props.traceId], () => {
  loadTimeline();
});
</script>

<style scoped>
.progress-timeline {
  @apply w-full;
}

.btn-refresh {
  @apply flex items-center gap-1 px-3 py-1.5 text-sm text-[#aaa] hover:text-white bg-[#202020] hover:bg-[#282828] rounded-lg transition-colors;
  border: 1px solid #303030;
}

.btn-refresh:disabled {
  @apply opacity-50 cursor-not-allowed;
}

.spinner {
  @apply w-8 h-8 border-4 border-[#303030] border-t-blue-500 rounded-full animate-spin;
}

/* 队列统计 */
.queue-stats {
  @apply flex items-center justify-center gap-4 mb-8 p-6 rounded-lg;
  background: linear-gradient(135deg, #202020 0%, #181818 100%);
  border: 1px solid #303030;
}

.stat-item {
  @apply flex flex-col items-center gap-1;
}

.stat-label {
  @apply text-xs text-[#aaa];
}

.stat-value {
  @apply text-3xl font-bold text-white;
}

.stat-item-processing .stat-value {
  color: #60a5fa;
}

.stat-item-completed .stat-value {
  color: #4ade80;
}

.stat-item-failed .stat-value {
  color: #f87171;
}

.stat-divider {
  @apply text-2xl font-bold text-[#666];
}

/* 队列容器 */
.queue-container {
  @apply flex gap-4;
}

.queue-section {
  @apply flex-1 flex flex-col rounded-lg overflow-hidden;
  background-color: #202020;
  border: 1px solid #303030;
  min-height: 500px;
  max-height: 600px;
}

.queue-section-processing {
  border-top: 3px solid #60a5fa;
}

.queue-section-completed {
  border-top: 3px solid #4ade80;
}

.queue-section-failed {
  border-top: 3px solid #f87171;
  max-width: 400px;
}

/* 区域头部 */
.queue-section-header {
  @apply flex items-center gap-3 p-4 border-b border-[#303030];
  background-color: #181818;
}

.section-icon {
  @apply w-8 h-8 rounded-lg flex items-center justify-center;
  background-color: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.section-icon-success {
  background-color: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.section-icon-error {
  background-color: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.section-title {
  @apply flex-1 font-semibold text-white;
}

.section-count {
  @apply px-3 py-1 text-sm font-bold rounded-full;
  background-color: #303030;
  color: #fff;
}

/* 队列项目容器 */
.queue-items {
  @apply flex-1 p-3 space-y-2;
}

.queue-items.scrollable {
  @apply overflow-y-auto;
}

/* 队列项目 */
.queue-item {
  @apply flex gap-3 p-3 rounded-lg transition-all;
  background-color: #181818;
  border: 1px solid #303030;
}

.queue-item-processing {
  border-left: 3px solid #60a5fa;
}

.queue-item-active {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid #60a5fa;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
  }
  50% {
    box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
  }
}

.queue-item-completed {
  border-left: 3px solid #4ade80;
}

.queue-item-failed {
  border-left: 3px solid #f87171;
  background-color: rgba(239, 68, 68, 0.05);
}

/* 项目指示器 */
.item-indicator {
  @apply flex flex-col items-center gap-1 flex-shrink-0;
}

.indicator-dot {
  @apply w-3 h-3 rounded-full;
  background-color: #60a5fa;
}

.queue-item-active .indicator-dot {
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.7;
  }
}

.queue-item-completed .indicator-dot {
  background-color: #4ade80;
}

.queue-item-failed .indicator-dot {
  background-color: #f87171;
}

.indicator-label {
  @apply text-xs font-medium;
  color: #60a5fa;
}

/* 项目内容 */
.item-content {
  @apply flex-1 min-w-0 space-y-2;
}

.item-header {
  @apply flex items-center justify-between gap-2;
}

.item-title {
  @apply text-sm font-medium text-white truncate flex-1;
}

.item-time {
  @apply text-xs text-[#666] whitespace-nowrap;
}

.item-meta {
  @apply flex items-center gap-2;
}

.meta-tag {
  @apply flex items-center gap-1 px-2 py-0.5 text-xs rounded;
  background-color: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
}

.item-message {
  @apply text-xs text-[#aaa];
}

.item-error {
  @apply flex items-start gap-1.5 text-xs p-2 rounded;
  background-color: rgba(239, 68, 68, 0.1);
  color: #f87171;
}

.item-url {
  @apply flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors;
}

.url-text {
  @apply truncate;
}

/* 流向箭头 */
.queue-flow-arrow {
  @apply flex flex-col items-center justify-center;
  width: 60px;
}

.queue-flow-arrow-error {
  @apply relative;
}

.flow-label {
  @apply mt-2 text-xs font-medium text-[#f87171];
}

/* 空状态 */
.queue-empty {
  @apply flex flex-col items-center justify-center py-12 text-center;
}
</style>
