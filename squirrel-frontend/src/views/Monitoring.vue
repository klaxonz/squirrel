<template>
  <div class="monitoring-page bg-[#0f0f0f] text-[#e0e0e0] min-h-screen overflow-y-auto">
    <!-- 顶部状态栏 -->
    <div class="border-b border-white/10">
      <div class="max-w-[1600px] mx-auto px-6 py-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-6">
            <h1 class="text-lg font-medium text-white">系统监控</h1>
            <div class="flex items-center gap-2 text-sm">
              <span class="w-2 h-2 rounded-full" :class="healthDotClass"></span>
              <span class="text-[#888]">{{ healthStatusText }}</span>
              <span class="text-[#888]">·</span>
              <span class="font-mono" :class="healthScoreClass">{{ dashboardData?.health?.score || 0 }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3 text-xs text-[#666]">
            <span>{{ lastUpdateTime }}</span>
            <button @click="refreshData" :disabled="loading" class="p-1.5 hover:bg-white/10 rounded transition-colors">
              <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="max-w-[1600px] mx-auto px-6 py-4 space-y-4">
      
      <!-- 概览指标 -->
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3">
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="text-xs text-[#666] mb-1">爬取任务</div>
          <div class="text-2xl font-bold font-mono">{{ dashboardData?.crawl?.total || 0 }}</div>
          <div class="flex gap-3 mt-2 text-xs">
            <span><span class="text-[#22c55e]">{{ dashboardData?.crawl?.success || 0 }}</span> 成功</span>
            <span><span class="text-[#ef4444]">{{ dashboardData?.crawl?.error || 0 }}</span> 失败</span>
          </div>
        </div>
        
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="text-xs text-[#666] mb-1">成功率</div>
          <div class="text-2xl font-bold font-mono" :class="successRateClass">{{ dashboardData?.crawl?.success_rate || 0 }}%</div>
          <div class="mt-2 w-full bg-[#252525] rounded-full h-1">
            <div class="h-1 rounded-full bg-[#22c55e] transition-all" :style="{ width: `${dashboardData?.crawl?.success_rate || 0}%` }"></div>
          </div>
        </div>
        
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="text-xs text-[#666] mb-1">发现视频</div>
          <div class="text-2xl font-bold font-mono">{{ dashboardData?.crawl?.videos_discovered || 0 }}</div>
          <div class="text-xs text-[#666] mt-2">跳过 {{ dashboardData?.crawl?.skipped || 0 }}</div>
        </div>
        
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="text-xs text-[#666] mb-1">队列积压</div>
          <div class="text-2xl font-bold font-mono" :class="queueDepthClass">{{ dashboardData?.queues?.total_depth || 0 }}</div>
          <div class="text-xs text-[#666] mt-2">消息 {{ dashboardData?.queues?.total_messages || 0 }}</div>
        </div>
        
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="text-xs text-[#666] mb-1">订阅更新</div>
          <div class="text-2xl font-bold font-mono">{{ dashboardData?.subscriptions?.total || 0 }}</div>
          <div class="flex gap-3 mt-2 text-xs">
            <span><span class="text-[#22c55e]">{{ dashboardData?.subscriptions?.success || 0 }}</span> 成功</span>
            <span><span class="text-[#ef4444]">{{ dashboardData?.subscriptions?.error || 0 }}</span> 失败</span>
          </div>
        </div>
        
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="text-xs text-[#666] mb-1">订阅发现</div>
          <div class="text-2xl font-bold font-mono">{{ dashboardData?.subscriptions?.videos_found || 0 }}</div>
          <div class="text-xs mt-2"><span class="text-[#22c55e]">{{ dashboardData?.subscriptions?.videos_enqueued || 0 }}</span> 已入队</div>
        </div>
      </div>

      <!-- 性能和错误 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-[#666]">性能指标</span>
            <span class="text-xs text-[#666]">单位: 秒</span>
          </div>
          <div class="grid grid-cols-4 gap-2 text-center">
            <div>
              <div class="text-lg font-mono">{{ dashboardData?.crawl?.avg_duration || 0 }}</div>
              <div class="text-xs text-[#666]">平均</div>
            </div>
            <div>
              <div class="text-lg font-mono">{{ dashboardData?.crawl?.p50_duration || 0 }}</div>
              <div class="text-xs text-[#666]">P50</div>
            </div>
            <div>
              <div class="text-lg font-mono text-[#f59e0b]">{{ dashboardData?.crawl?.p95_duration || 0 }}</div>
              <div class="text-xs text-[#666]">P95</div>
            </div>
            <div>
              <div class="text-lg font-mono text-[#ef4444]">{{ dashboardData?.crawl?.max_duration || 0 }}</div>
              <div class="text-xs text-[#666]">最大</div>
            </div>
          </div>
        </div>
        
        <div class="bg-[#161616] rounded-lg p-3 border border-white/5">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-[#666]">错误统计</span>
            <span class="text-sm font-mono text-[#ef4444]">{{ dashboardData?.errors?.total || 0 }}</span>
          </div>
          <div v-if="dashboardData?.errors?.by_type?.length" class="flex flex-wrap gap-1.5">
            <span v-for="error in dashboardData.errors.by_type.slice(0, 8)" :key="error.type" class="px-2 py-0.5 bg-[#ef4444]/10 text-[#ef4444] rounded text-xs">
              {{ error.type }}: {{ error.count }}
            </span>
          </div>
          <div v-else class="text-xs text-[#444]">暂无错误</div>
        </div>
      </div>

      <!-- 站点统计表格 -->
      <div class="bg-[#161616] rounded-lg border border-white/5">
        <div class="px-4 py-2.5 border-b border-white/5 flex items-center justify-between">
          <span class="text-sm font-medium text-white">站点统计</span>
          <span class="text-xs text-[#666]">{{ dashboardData?.crawl?.by_site?.length || 0 }} 个站点</span>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-[#666] border-b border-white/5">
                <th class="text-left px-4 py-2 font-medium">站点</th>
                <th class="text-right px-3 py-2 font-medium">成功率</th>
                <th class="text-right px-3 py-2 font-medium">成功</th>
                <th class="text-right px-3 py-2 font-medium">失败</th>
                <th class="text-right px-3 py-2 font-medium">跳过</th>
                <th class="text-right px-3 py-2 font-medium">视频</th>
                <th class="text-right px-3 py-2 font-medium">队列</th>
                <th class="text-right px-3 py-2 font-medium">平均耗时</th>
                <th class="text-right px-3 py-2 font-medium">P95</th>
                <th class="text-right px-3 py-2 font-medium">订阅发现</th>
                <th class="text-right px-4 py-2 font-medium">订阅入队</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="site in dashboardData?.crawl?.by_site" :key="site.site" class="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <span class="w-6 h-6 rounded bg-[#252525] flex items-center justify-center text-[10px] font-bold uppercase text-[#888]">{{ site.site.slice(0, 2) }}</span>
                    <span class="font-medium text-white">{{ site.site }}</span>
                  </div>
                </td>
                <td class="text-right px-3 py-2.5 font-mono" :class="getSiteRateClass(site.success_rate)">{{ site.success_rate }}%</td>
                <td class="text-right px-3 py-2.5 font-mono text-[#22c55e]">{{ site.success }}</td>
                <td class="text-right px-3 py-2.5 font-mono text-[#ef4444]">{{ site.error }}</td>
                <td class="text-right px-3 py-2.5 font-mono text-[#666]">{{ site.skipped }}</td>
                <td class="text-right px-3 py-2.5 font-mono">{{ site.videos }}</td>
                <td class="text-right px-3 py-2.5 font-mono" :class="site.queue_depth > 100 ? 'text-[#ef4444]' : site.queue_depth > 50 ? 'text-[#f59e0b]' : 'text-[#666]'">{{ site.queue_depth || 0 }}</td>
                <td class="text-right px-3 py-2.5 font-mono text-[#888]">{{ site.avg_duration || '-' }}s</td>
                <td class="text-right px-3 py-2.5 font-mono text-[#888]">{{ site.p95_duration || '-' }}s</td>
                <td class="text-right px-3 py-2.5 font-mono">{{ getSubscriptionBySite(site.site)?.videos_found || '-' }}</td>
                <td class="text-right px-4 py-2.5 font-mono text-[#22c55e]">{{ getSubscriptionBySite(site.site)?.videos_enqueued || '-' }}</td>
              </tr>
            </tbody>
          </table>
          
          <div v-if="!dashboardData?.crawl?.by_site?.length" class="text-center text-[#444] py-8 text-sm">
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

const loading = ref(false)
const dashboardData = ref(null)
const lastUpdateTime = ref('')
let refreshTimer = null

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

const refreshData = () => {
  fetchDashboard()
}

// 健康状态
const healthDotClass = computed(() => {
  const status = dashboardData.value?.health?.status
  if (status === 'healthy') return 'bg-[#22c55e]'
  if (status === 'degraded') return 'bg-[#f59e0b]'
  return 'bg-[#ef4444]'
})

const healthStatusText = computed(() => {
  const status = dashboardData.value?.health?.status
  if (status === 'healthy') return '正常'
  if (status === 'degraded') return '降级'
  if (status === 'critical') return '异常'
  return '未知'
})

const healthScoreClass = computed(() => {
  const score = dashboardData.value?.health?.score || 0
  if (score >= 80) return 'text-[#22c55e]'
  if (score >= 50) return 'text-[#f59e0b]'
  return 'text-[#ef4444]'
})

const successRateClass = computed(() => {
  const rate = dashboardData.value?.crawl?.success_rate || 0
  if (rate >= 80) return 'text-[#22c55e]'
  if (rate >= 50) return 'text-[#f59e0b]'
  return 'text-[#ef4444]'
})

const queueDepthClass = computed(() => {
  const depth = dashboardData.value?.queues?.total_depth || 0
  if (depth < 100) return 'text-[#e0e0e0]'
  if (depth < 500) return 'text-[#f59e0b]'
  return 'text-[#ef4444]'
})

const getSiteRateClass = (rate) => {
  if (rate >= 80) return 'text-[#22c55e]'
  if (rate >= 50) return 'text-[#f59e0b]'
  return 'text-[#ef4444]'
}

const getSubscriptionBySite = (siteName) => {
  const subscriptions = dashboardData.value?.subscriptions?.by_site || []
  return subscriptions.find(s => s.site === siteName) || null
}

onMounted(() => {
  fetchDashboard()
  refreshTimer = setInterval(fetchDashboard, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.monitoring-page {
  font-feature-settings: "tnum";
}
</style>
