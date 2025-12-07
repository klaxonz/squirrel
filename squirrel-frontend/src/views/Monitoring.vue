<template>
  <div class="monitoring-page bg-[#0f0f0f] text-white min-h-screen overflow-y-auto">
    <!-- 顶部状态栏 -->
    <div class="border-b border-white/10">
      <div class="max-w-[1800px] mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <h1 class="text-xl font-medium">系统监控</h1>
            <div class="flex items-center gap-2 text-sm text-[#aaaaaa]">
              <span class="w-2 h-2 rounded-full" :class="healthDotClass"></span>
              <span>{{ healthStatusText }}</span>
            </div>
          </div>
          
          <div class="flex items-center gap-4">
            <span class="text-xs text-[#666]">{{ lastUpdateTime }}</span>
            <button
              @click="refreshData"
              :disabled="loading"
              class="p-2 hover:bg-white/10 rounded-lg transition-colors"
              title="刷新"
            >
              <svg class="w-5 h-5" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="max-w-[1800px] mx-auto px-6 py-6 space-y-6">
      
      <!-- 健康度概览 -->
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <!-- 健康分数 -->
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-xs text-[#666] mb-2">健康分数</div>
          <div class="flex items-end gap-2">
            <span class="text-4xl font-bold" :class="healthScoreClass">{{ dashboardData?.health?.score || 0 }}</span>
            <span class="text-lg text-[#666] mb-1">/100</span>
          </div>
          <div v-if="dashboardData?.health?.issues?.length" class="mt-3 pt-3 border-t border-white/5">
            <div v-for="issue in dashboardData.health.issues.slice(0, 2)" :key="issue" class="text-xs text-[#f44336] flex items-start gap-1 mt-1">
              <span>•</span>
              <span>{{ issue }}</span>
            </div>
          </div>
        </div>
        
        <!-- 爬取总数 -->
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-xs text-[#666] mb-2">爬取任务</div>
          <div class="text-4xl font-bold">{{ dashboardData?.crawl?.total || 0 }}</div>
          <div class="mt-3 grid grid-cols-3 gap-2 text-center">
            <div>
              <div class="text-lg font-semibold text-[#00c853]">{{ dashboardData?.crawl?.success || 0 }}</div>
              <div class="text-xs text-[#666]">成功</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-[#f44336]">{{ dashboardData?.crawl?.error || 0 }}</div>
              <div class="text-xs text-[#666]">失败</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-[#ffc107]">{{ dashboardData?.crawl?.skipped || 0 }}</div>
              <div class="text-xs text-[#666]">跳过</div>
            </div>
          </div>
        </div>
        
        <!-- 发现视频 -->
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-xs text-[#666] mb-2">发现视频</div>
          <div class="text-4xl font-bold text-[#3b82f6]">{{ dashboardData?.crawl?.videos_discovered || 0 }}</div>
          <div class="mt-3 pt-3 border-t border-white/5">
            <div class="flex justify-between items-center">
              <span class="text-xs text-[#666]">成功率</span>
              <span class="text-sm font-medium" :class="successRateClass">{{ dashboardData?.crawl?.success_rate || 0 }}%</span>
            </div>
            <div class="mt-2 w-full bg-[#333] rounded-full h-1.5">
              <div class="h-1.5 rounded-full transition-all" :class="successRateBarClass" :style="{ width: `${dashboardData?.crawl?.success_rate || 0}%` }"></div>
            </div>
          </div>
        </div>
        
        <!-- 队列积压 -->
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-xs text-[#666] mb-2">队列积压</div>
          <div class="text-4xl font-bold" :class="queueDepthClass">{{ dashboardData?.queues?.total_depth || 0 }}</div>
          <div class="mt-3 pt-3 border-t border-white/5">
            <div class="flex justify-between items-center">
              <span class="text-xs text-[#666]">已发布消息</span>
              <span class="text-sm font-medium">{{ dashboardData?.queues?.total_messages || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 订阅更新统计 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-xs text-[#666] mb-2">订阅更新</div>
          <div class="text-4xl font-bold">{{ dashboardData?.subscriptions?.total || 0 }}</div>
          <div class="mt-3 grid grid-cols-3 gap-2 text-center">
            <div>
              <div class="text-lg font-semibold text-[#00c853]">{{ dashboardData?.subscriptions?.success || 0 }}</div>
              <div class="text-xs text-[#666]">成功</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-[#f44336]">{{ dashboardData?.subscriptions?.error || 0 }}</div>
              <div class="text-xs text-[#666]">失败</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-[#ffc107]">{{ dashboardData?.subscriptions?.skipped || 0 }}</div>
              <div class="text-xs text-[#666]">跳过</div>
            </div>
          </div>
        </div>
        
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-xs text-[#666] mb-2">订阅发现视频</div>
          <div class="text-4xl font-bold text-[#3b82f6]">{{ dashboardData?.subscriptions?.videos_found || 0 }}</div>
          <div class="mt-3 pt-3 border-t border-white/5">
            <div class="flex justify-between items-center">
              <span class="text-xs text-[#666]">已入队</span>
              <span class="text-sm font-medium text-[#00c853]">{{ dashboardData?.subscriptions?.videos_enqueued || 0 }}</span>
            </div>
            <div class="flex justify-between items-center mt-1">
              <span class="text-xs text-[#666]">成功率</span>
              <span class="text-sm font-medium" :class="subSuccessRateClass">{{ dashboardData?.subscriptions?.success_rate || 0 }}%</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 错误统计和性能指标 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- 错误统计 -->
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="flex items-center justify-between mb-3">
            <div class="text-sm font-medium">错误统计</div>
            <span class="text-lg font-bold text-[#f44336]">{{ dashboardData?.errors?.total || 0 }}</span>
          </div>
          <div v-if="dashboardData?.errors?.by_type?.length" class="flex flex-wrap gap-2">
            <span
              v-for="error in dashboardData.errors.by_type.slice(0, 6)"
              :key="error.type"
              class="px-3 py-1.5 bg-[#f44336]/10 text-[#f44336] rounded-lg text-sm"
            >
              {{ error.type }}: {{ error.count }}
            </span>
          </div>
          <div v-else class="text-[#666] text-sm">暂无错误</div>
        </div>
        
        <!-- 性能指标 -->
        <div class="bg-[#1a1a1a] rounded-xl p-5 border border-white/5">
          <div class="text-sm font-medium mb-3">性能指标</div>
          <div class="grid grid-cols-4 gap-3 text-center">
            <div class="p-2 bg-[#252525] rounded">
              <div class="text-lg font-bold">{{ dashboardData?.crawl?.avg_duration || 0 }}s</div>
              <div class="text-xs text-[#666]">平均</div>
            </div>
            <div class="p-2 bg-[#252525] rounded">
              <div class="text-lg font-bold">{{ dashboardData?.crawl?.p50_duration || 0 }}s</div>
              <div class="text-xs text-[#666]">P50</div>
            </div>
            <div class="p-2 bg-[#252525] rounded">
              <div class="text-lg font-bold text-[#ffc107]">{{ dashboardData?.crawl?.p95_duration || 0 }}s</div>
              <div class="text-xs text-[#666]">P95</div>
            </div>
            <div class="p-2 bg-[#252525] rounded">
              <div class="text-lg font-bold text-[#f44336]">{{ dashboardData?.crawl?.max_duration || 0 }}s</div>
              <div class="text-xs text-[#666]">最大</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 站点统计 -->
      <div class="bg-[#1a1a1a] rounded-xl border border-white/5">
          <div class="px-5 py-4 border-b border-white/5 flex items-center justify-between">
            <h2 class="font-medium">站点统计</h2>
            <span class="text-xs text-[#666]">{{ dashboardData?.crawl?.by_site?.length || 0 }} 个站点</span>
          </div>
          
          <div class="p-5">
            <div v-if="dashboardData?.crawl?.by_site?.length" class="space-y-3">
              <div
                v-for="site in dashboardData.crawl.by_site"
                :key="site.site"
                class="p-4 bg-[#252525] rounded-lg hover:bg-[#2a2a2a] transition-colors"
              >
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-[#333] flex items-center justify-center text-xs font-bold uppercase">
                      {{ site.site.slice(0, 2) }}
                    </div>
                    <div>
                      <div class="font-medium">{{ site.site }}</div>
                      <div class="text-xs text-[#666]">{{ site.total }} 任务</div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-lg font-semibold" :class="getSiteSuccessRateClass(site.success_rate)">
                      {{ site.success_rate }}%
                    </div>
                    <div class="text-xs text-[#666]">成功率</div>
                  </div>
                </div>
                
                <div class="grid grid-cols-5 gap-2 text-center">
                  <div class="p-2 bg-[#1a1a1a] rounded">
                    <div class="text-sm font-medium text-[#00c853]">{{ site.success }}</div>
                    <div class="text-xs text-[#666]">成功</div>
                  </div>
                  <div class="p-2 bg-[#1a1a1a] rounded">
                    <div class="text-sm font-medium text-[#f44336]">{{ site.error }}</div>
                    <div class="text-xs text-[#666]">失败</div>
                  </div>
                  <div class="p-2 bg-[#1a1a1a] rounded">
                    <div class="text-sm font-medium text-[#ffc107]">{{ site.skipped }}</div>
                    <div class="text-xs text-[#666]">跳过</div>
                  </div>
                  <div class="p-2 bg-[#1a1a1a] rounded">
                    <div class="text-sm font-medium text-[#3b82f6]">{{ site.videos }}</div>
                    <div class="text-xs text-[#666]">视频</div>
                  </div>
                  <div class="p-2 bg-[#1a1a1a] rounded">
                    <div class="text-sm font-medium" :class="site.queue_depth > 100 ? 'text-[#f44336]' : site.queue_depth > 50 ? 'text-[#ffc107]' : 'text-[#aaa]'">{{ site.queue_depth || 0 }}</div>
                    <div class="text-xs text-[#666]">队列</div>
                  </div>
                </div>
                
                <!-- 性能指标 -->
                <div v-if="site.avg_duration > 0" class="mt-3 pt-3 border-t border-white/5">
                  <div class="text-xs text-[#666] mb-2">性能指标</div>
                  <div class="grid grid-cols-4 gap-2 text-center text-xs">
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium">{{ site.avg_duration }}s</div>
                      <div class="text-[#666]">平均</div>
                    </div>
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium">{{ site.p50_duration }}s</div>
                      <div class="text-[#666]">P50</div>
                    </div>
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium">{{ site.p95_duration }}s</div>
                      <div class="text-[#666]">P95</div>
                    </div>
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium">{{ site.max_duration }}s</div>
                      <div class="text-[#666]">最大</div>
                    </div>
                  </div>
                </div>
                
                <!-- 订阅统计 -->
                <div v-if="getSubscriptionBySite(site.site)" class="mt-3 pt-3 border-t border-white/5">
                  <div class="text-xs text-[#666] mb-2">订阅更新</div>
                  <div class="grid grid-cols-4 gap-2 text-center text-xs">
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium text-[#3b82f6]">{{ getSubscriptionBySite(site.site).videos_found }}</div>
                      <div class="text-[#666]">发现</div>
                    </div>
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium text-[#00c853]">{{ getSubscriptionBySite(site.site).videos_enqueued }}</div>
                      <div class="text-[#666]">入队</div>
                    </div>
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium">{{ getSubscriptionBySite(site.site).success }}</div>
                      <div class="text-[#666]">成功</div>
                    </div>
                    <div class="p-1.5 bg-[#1a1a1a] rounded">
                      <div class="font-medium text-[#f44336]">{{ getSubscriptionBySite(site.site).error }}</div>
                      <div class="text-[#666]">失败</div>
                    </div>
                  </div>
                </div>
                
                <!-- 错误详情 -->
                <div v-if="Object.keys(site.errors || {}).length > 0" class="mt-3 pt-3 border-t border-white/5">
                  <div class="text-xs text-[#666] mb-2">错误类型</div>
                  <div class="flex flex-wrap gap-2">
                    <span
                      v-for="(count, type) in site.errors"
                      :key="type"
                      class="px-2 py-1 bg-[#f44336]/10 text-[#f44336] rounded text-xs"
                    >
                      {{ type }}: {{ count }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <div v-else class="text-center text-[#666] py-12">
              暂无站点数据
            </div>
          </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from '../utils/axios'

// 状态
const loading = ref(false)
const dashboardData = ref(null)
const lastUpdateTime = ref('')
let refreshTimer = null

// 获取仪表板数据
const fetchDashboard = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/metrics/dashboard')
    dashboardData.value = response.data
    lastUpdateTime.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('Failed to fetch dashboard:', error)
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  fetchDashboard()
}

// 计算属性
const healthDotClass = computed(() => {
  const status = dashboardData.value?.health?.status
  if (status === 'healthy') return 'bg-[#00c853]'
  if (status === 'degraded') return 'bg-[#ffc107]'
  if (status === 'critical') return 'bg-[#f44336] animate-pulse'
  return 'bg-[#666]'
})

const healthStatusText = computed(() => {
  const status = dashboardData.value?.health?.status
  if (status === 'healthy') return '系统正常'
  if (status === 'degraded') return '性能降级'
  if (status === 'critical') return '系统异常'
  return '未知'
})

const healthScoreClass = computed(() => {
  const score = dashboardData.value?.health?.score || 0
  if (score >= 80) return 'text-[#00c853]'
  if (score >= 50) return 'text-[#ffc107]'
  return 'text-[#f44336]'
})

const successRateClass = computed(() => {
  const rate = dashboardData.value?.crawl?.success_rate || 0
  if (rate >= 80) return 'text-[#00c853]'
  if (rate >= 50) return 'text-[#ffc107]'
  return 'text-[#f44336]'
})

const successRateBarClass = computed(() => {
  const rate = dashboardData.value?.crawl?.success_rate || 0
  if (rate >= 80) return 'bg-[#00c853]'
  if (rate >= 50) return 'bg-[#ffc107]'
  return 'bg-[#f44336]'
})

const queueDepthClass = computed(() => {
  const depth = dashboardData.value?.queues?.total_depth || 0
  if (depth < 100) return 'text-[#00c853]'
  if (depth < 500) return 'text-[#ffc107]'
  return 'text-[#f44336]'
})

// 获取站点对应的订阅数据
const getSubscriptionBySite = (siteName) => {
  const subscriptions = dashboardData.value?.subscriptions?.by_site || []
  return subscriptions.find(s => s.site === siteName) || null
}

const subSuccessRateClass = computed(() => {
  const rate = dashboardData.value?.subscriptions?.success_rate || 0
  if (rate >= 80) return 'text-[#00c853]'
  if (rate >= 50) return 'text-[#ffc107]'
  return 'text-[#f44336]'
})

// 方法
const getSiteSuccessRateClass = (rate) => {
  if (rate >= 80) return 'text-[#00c853]'
  if (rate >= 50) return 'text-[#ffc107]'
  return 'text-[#f44336]'
}


// 生命周期
onMounted(() => {
  fetchDashboard()
  // 30秒自动刷新
  refreshTimer = setInterval(fetchDashboard, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
