<template>
  <div class="progress-monitor-page flex flex-col h-full bg-[#0f0f0f] text-white">
    <!-- 顶部操作栏 -->
    <div class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8 py-4">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="text-xl font-semibold text-white">视频提取队列</h1>
          <p class="text-xs text-[#aaa] mt-1">实时查看视频提取进度，3秒自动刷新</p>
        </div>
        <div class="flex gap-2">
          <button 
            @click="clearCache"
            class="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-full flex items-center transition-colors text-sm"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            清空缓存
          </button>
          <button 
            @click="refreshAll"
            :disabled="loading"
            class="px-4 py-2 bg-white/10 hover:bg-white/15 text-white rounded-full flex items-center transition-colors text-sm disabled:opacity-50"
          >
            <svg 
              class="w-4 h-4 mr-2" 
              :class="{ 'animate-spin': loading }"
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            刷新全部
          </button>
        </div>
      </div>

      <!-- 队列统计 -->
      <div class="queue-stats-bar">
        <div class="stat-item">
          <div class="stat-label">队列总数</div>
          <div class="stat-value">{{ allVideos.length }}</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="stat-item stat-processing">
          <div class="stat-label">处理中</div>
          <div class="stat-value">{{ processingVideos.length }}</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="stat-item stat-completed">
          <div class="stat-label">已完成</div>
          <div class="stat-value">{{ completedVideos.length }}</div>
        </div>
        <div class="flow-arrow">×</div>
        <div class="stat-item stat-failed">
          <div class="stat-label">失败</div>
          <div class="stat-value">{{ failedVideos.length }}</div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="flex-1 overflow-hidden">
      <div class="max-w-[1800px] mx-auto w-full h-full px-4 sm:px-6 lg:px-8 pb-6">
        <!-- 队列容器 -->
        <div class="queue-container h-full">
          <!-- 正在处理 -->
          <div class="queue-section queue-section-processing">
            <div class="queue-section-header">
              <div class="header-content">
                <div class="section-icon">
                  <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
                <div class="section-title">正在处理</div>
              </div>
              <div class="section-count">{{ processingVideos.length }}</div>
            </div>
            
            <div class="queue-items" v-if="processingVideos.length > 0">
              <div 
                v-for="(video, index) in processingVideos" 
                :key="index"
                class="queue-item queue-item-processing"
                :class="{ 'queue-item-current': index === 0 }"
              >
                <div class="item-indicator">
                  <div class="indicator-dot"></div>
                  <div class="indicator-label">{{ index === 0 ? '当前' : '等待' }}</div>
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
                  
                  <a :href="video.url" target="_blank" class="item-url" :title="video.url">
                    <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    <span class="url-text">{{ video.url }}</span>
                  </a>
                </div>
              </div>
            </div>
            
            <div v-else class="queue-empty">
              <svg class="w-12 h-12 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <p class="text-sm text-[#666] mt-3">暂无处理中的视频</p>
            </div>
          </div>

          <!-- 流向箭头 -->
          <div class="queue-flow-arrow">
            <svg class="w-10 h-10 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </div>

          <!-- 已完成 -->
          <div class="queue-section queue-section-completed">
            <div class="queue-section-header">
              <div class="header-content">
                <div class="section-icon section-icon-success">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div class="section-title">已完成</div>
              </div>
              <div class="section-count">{{ completedVideos.length }}</div>
            </div>
            
            <div class="queue-items" v-if="completedVideos.length > 0">
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
              <svg class="w-12 h-12 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p class="text-sm text-[#666] mt-3">暂无完成的视频</p>
            </div>
          </div>

          <!-- 流向箭头（失败） -->
          <div class="queue-flow-arrow queue-flow-error">
            <svg class="w-10 h-10 text-[#f87171]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17l5-5m0 0l-5-5m5 5H6" />
            </svg>
            <div class="flow-label">异常</div>
          </div>

          <!-- 失败 -->
          <div class="queue-section queue-section-failed">
            <div class="queue-section-header">
              <div class="header-content">
                <div class="section-icon section-icon-error">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <div class="section-title">失败</div>
              </div>
              <div class="section-count">{{ failedVideos.length }}</div>
            </div>
            
            <div class="queue-items" v-if="failedVideos.length > 0">
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
              <svg class="w-12 h-12 text-[#666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="text-sm text-[#666] mt-3">暂无失败的视频</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useProgressApi } from '../composables/useProgressApi';

const { getProgressList } = useProgressApi();

const loading = ref(false);
const progressList = ref([]);
const subscriptionCache = ref(new Map());
// 视频状态缓存 - 仅内存缓存，保证实时性
const videoStateCache = ref(new Map());

// 清空缓存
const clearCache = () => {
  if (confirm('确定要清空所有视频记录吗？')) {
    videoStateCache.value.clear();
    loadProgressList();
  }
};

const loadProgressList = async () => {
  loading.value = true;
  try {
    const result = await getProgressList({
      scope: 'all',
      page: 1,
      pageSize: 5000  // 提高到5000，确保能获取到所有相关事件
    });
    
    if (result.success && result.data) {
      progressList.value = result.data.list || [];
      
      // 加载订阅信息
      const subscriptionIds = [...new Set(
        progressList.value
          .map(item => item.subscription_id)
          .filter(id => id != null)
      )];
      
      if (subscriptionIds.length > 0) {
        await loadSubscriptionInfo(subscriptionIds);
      }
    }
  } finally {
    loading.value = false;
  }
};

const loadSubscriptionInfo = async (subscriptionIds) => {
  // 移除了 getSubscriptionDetail 调用，订阅信息不再加载
  return;
};

const refreshAll = () => {
  loadProgressList();
};

// 更新视频状态缓存
const updateVideoCache = () => {
  for (const item of progressList.value) {
    const eventType = item.event_type;
    
    if (eventType && eventType.startsWith('video_extraction_')) {
      const url = item.url;
      if (!url) continue;
      
      // 如果缓存中没有这个视频，创建新记录
      if (!videoStateCache.value.has(url)) {
        videoStateCache.value.set(url, {
          url: url,
          status: 'progress',
          message: '',
          error: null,
          time: item.created_at,
          subscription_id: item.subscription_id
        });
      }
      
      const video = videoStateCache.value.get(url);
      
      // 更新视频状态（只允许状态向前推进，不允许回退）
      if (eventType === 'video_extraction_start') {
        // 如果当前是 progress 状态，可以更新时间和消息
        if (video.status === 'progress') {
          video.message = item.message || '开始提取';
          video.time = item.created_at;
          video.subscription_id = item.subscription_id;
        }
      } else if (eventType === 'video_extraction_complete') {
        // 完成状态可以覆盖 progress 状态
        if (video.status === 'progress' || video.status === 'success') {
          video.status = 'success';
          video.message = item.message || '提取完成';
          video.time = item.created_at;
        }
      } else if (eventType === 'video_extraction_error') {
        // 失败状态可以覆盖 progress 状态
        if (video.status === 'progress' || video.status === 'error') {
          video.status = 'error';
          video.message = '提取失败';
          video.error = item.error_message || item.message;
          video.time = item.created_at;
        }
      }
    }
  }
};

// 从缓存中获取所有视频
const allVideos = computed(() => {
  // 每次计算前先更新缓存
  updateVideoCache();
  
  // 返回缓存中的所有视频
  return Array.from(videoStateCache.value.values());
});

// 按状态分类
const processingVideos = computed(() => 
  allVideos.value
    .filter(v => v.status === 'progress')
    .sort((a, b) => new Date(a.time) - new Date(b.time))
);

const completedVideos = computed(() => 
  allVideos.value
    .filter(v => v.status === 'success')
    .sort((a, b) => new Date(b.time) - new Date(a.time))
);

const failedVideos = computed(() => 
  allVideos.value
    .filter(v => v.status === 'error')
    .sort((a, b) => new Date(b.time) - new Date(a.time))
);

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

const getSubscriptionName = (subscriptionId) => {
  if (!subscriptionId) return '';
  const subscription = subscriptionCache.value.get(subscriptionId);
  return subscription ? subscription.name : '';
};

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
  // 加载进度列表
  loadProgressList();
  
  // 自动刷新 - 缩短到3秒以保证实时性
  setInterval(loadProgressList, 3000);
});
</script>

<style scoped>
.progress-monitor-page {
  min-height: 100vh;
}

/* 队列统计条 */
.queue-stats-bar {
  @apply flex items-center justify-center gap-6 p-6 rounded-lg mb-6;
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

.stat-processing .stat-value {
  color: #60a5fa;
}

.stat-completed .stat-value {
  color: #4ade80;
}

.stat-failed .stat-value {
  color: #f87171;
}

.flow-arrow {
  @apply text-2xl font-bold text-[#666];
}

/* 队列容器 */
.queue-container {
  @apply flex gap-4;
  height: calc(100vh - 280px);
}

.queue-section {
  @apply flex-1 flex flex-col rounded-lg overflow-hidden;
  background-color: #202020;
  border: 1px solid #303030;
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
  @apply flex items-center justify-between p-4 border-b border-[#303030] flex-shrink-0;
  background-color: #181818;
}

.header-content {
  @apply flex items-center gap-3;
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
  @apply font-semibold text-white;
}

.section-count {
  @apply px-3 py-1 text-sm font-bold rounded-full;
  background-color: #303030;
  color: #fff;
}

/* 队列项目 */
.queue-items {
  @apply flex-1 overflow-y-auto p-3 space-y-2;
}

.queue-item {
  @apply flex gap-3 p-3 rounded-lg transition-all;
  background-color: #181818;
  border: 1px solid #303030;
}

.queue-item-processing {
  border-left: 3px solid #60a5fa;
}

.queue-item-current {
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

.queue-item-current .indicator-dot {
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

.queue-flow-error {
  @apply relative;
}

.flow-label {
  @apply mt-2 text-xs font-medium text-[#f87171];
}

/* 空状态 */
.queue-empty {
  @apply flex-1 flex flex-col items-center justify-center py-12;
}
</style>
