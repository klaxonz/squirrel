<template>
  <div class="monitoring-page bg-bg-primary text-text-primary min-h-screen overflow-y-auto">
    <!-- 顶部状态栏 -->
    <div class="border-b border-white/10">
      <div class="max-w-[1600px] mx-auto px-6 py-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-6">
            <h1 class="text-lg font-medium text-white">系统监控</h1>
            <div class="flex items-center gap-2 text-sm">
              <span class="w-2 h-2 rounded-full" :class="healthDotClass"></span>
              <span class="text-text-secondary">{{ healthStatusText }}</span>
              <span class="text-text-secondary">·</span>
              <span class="font-mono" :class="healthScoreClass">{{ dashboardData?.health?.score || 0 }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3 text-xs text-text-tertiary">
            <span>{{ lastUpdateTime }}</span>
            <button @click="refreshData" :disabled="loading" class="p-1.5 hover:bg-white/10 rounded transition-colors">
              <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': loading }" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="max-w-[1600px] mx-auto px-6 py-4 space-y-4">
      
      <!-- 概览指标 -->
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3">
        <StatsCard
          title="爬取任务"
          :value="dashboardData?.crawl?.total || 0"
          :hover-effect="true"
        >
          <template #subtitle>
            <div class="flex gap-3">
              <span><span class="text-color-success">{{ dashboardData?.crawl?.success || 0 }}</span> 成功</span>
              <span><span class="text-color-error">{{ dashboardData?.crawl?.error || 0 }}</span> 失败</span>
            </div>
          </template>
        </StatsCard>

        <StatsCard
          title="成功率"
          :value="dashboardData?.crawl?.success_rate || 0"
          format="percentage"
          :value-color="getSuccessRateColor()"
          :show-progress="true"
          :progress-percent="dashboardData?.crawl?.success_rate || 0"
          :progress-variant="getSuccessRateColor()"
          :hover-effect="true"
        />

        <StatsCard
          title="发现视频"
          :value="dashboardData?.crawl?.videos_discovered || 0"
          :hover-effect="true"
        >
          <template #subtitle>
            跳过 {{ dashboardData?.crawl?.skipped || 0 }}
          </template>
        </StatsCard>

        <StatsCard
          title="队列积压"
          :value="dashboardData?.queues?.total_depth || 0"
          :value-color="getQueueDepthColor()"
          :hover-effect="true"
        >
          <template #subtitle>
            消息 {{ dashboardData?.queues?.total_messages || 0 }}
          </template>
        </StatsCard>

        <StatsCard
          title="订阅更新"
          :value="dashboardData?.subscriptions?.total || 0"
          :hover-effect="true"
        >
          <template #subtitle>
            <div class="flex gap-3">
              <span><span class="text-color-success">{{ dashboardData?.subscriptions?.success || 0 }}</span> 成功</span>
              <span><span class="text-color-error">{{ dashboardData?.subscriptions?.error || 0 }}</span> 失败</span>
            </div>
          </template>
        </StatsCard>

        <StatsCard
          title="订阅发现"
          :value="dashboardData?.subscriptions?.videos_found || 0"
          :hover-effect="true"
        >
          <template #subtitle>
            <span class="text-color-success">{{ dashboardData?.subscriptions?.videos_enqueued || 0 }}</span> 已入队
          </template>
        </StatsCard>
      </div>

      <!-- 性能和错误 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Card class="p-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-text-tertiary">性能指标</span>
            <span class="text-xs text-text-tertiary">单位: 秒</span>
          </div>
          <div class="grid grid-cols-4 gap-3 text-center">
            <div>
              <div class="text-lg font-mono text-text-primary">{{ dashboardData?.crawl?.avg_duration || 0 }}</div>
              <div class="text-xs text-text-tertiary">平均</div>
            </div>
            <div>
              <div class="text-lg font-mono text-text-primary">{{ dashboardData?.crawl?.p50_duration || 0 }}</div>
              <div class="text-xs text-text-tertiary">P50</div>
            </div>
            <div>
              <div class="text-lg font-mono text-color-warning">{{ dashboardData?.crawl?.p95_duration || 0 }}</div>
              <div class="text-xs text-text-tertiary">P95</div>
            </div>
            <div>
              <div class="text-lg font-mono text-color-error">{{ dashboardData?.crawl?.max_duration || 0 }}</div>
              <div class="text-xs text-text-tertiary">最大</div>
            </div>
          </div>
        </Card>

        <Card class="p-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-text-tertiary">错误统计</span>
            <span class="text-sm font-mono text-color-error">{{ dashboardData?.errors?.total || 0 }}</span>
          </div>
          <div v-if="dashboardData?.errors?.by_type?.length" class="flex flex-wrap gap-1.5">
            <StatusBadge
              v-for="error in dashboardData.errors.by_type.slice(0, 8)"
              :key="error.type"
              variant="error"
              size="xs"
              :label="`${error.type}: ${error.count}`"
            />
          </div>
          <div v-else class="text-xs text-text-muted">暂无错误</div>
        </Card>
      </div>
      
      <!-- 站点统计表格 -->
      <DataTable
        :columns="siteTableColumns"
        :data="dashboardData?.crawl?.by_site || []"
      >
        <template #header>
          <span class="text-sm font-medium text-text-primary">站点统计</span>
          <span class="text-xs text-text-tertiary">{{ dashboardData?.crawl?.by_site?.length || 0 }} 个站点</span>
        </template>

        <template #column-site="{ row }">
          <div class="flex items-center gap-2">
            <span class="w-6 h-6 rounded bg-bg-tertiary flex items-center justify-center text-[10px] font-bold uppercase text-text-muted">{{ row.site.slice(0, 2) }}</span>
            <span class="font-medium text-text-primary">{{ row.site }}</span>
          </div>
        </template>

        <template #column-success_rate="{ value }">
          <span class="font-mono" :class="getSiteRateClass(value)">{{ value }}%</span>
        </template>

        <template #column-success="{ value }">
          <span class="font-mono text-color-success">{{ value }}</span>
        </template>

        <template #column-error="{ value }">
          <span class="font-mono text-color-error">{{ value }}</span>
        </template>

        <template #column-skipped="{ value }">
          <span class="font-mono text-text-tertiary">{{ value }}</span>
        </template>

        <template #column-videos="{ value }">
          <span class="font-mono text-text-primary">{{ value }}</span>
        </template>

        <template #column-queue_depth="{ value }">
          <span class="font-mono" :class="value > 100 ? 'text-color-error' : value > 50 ? 'text-color-warning' : 'text-text-tertiary'">{{ value || 0 }}</span>
        </template>

        <template #column-avg_duration="{ value }">
          <span class="font-mono text-text-secondary">{{ value || '-' }}s</span>
        </template>

        <template #column-p95_duration="{ value }">
          <span class="font-mono text-text-secondary">{{ value || '-' }}s</span>
        </template>

        <template #column-videos_found="{ row }">
          <span class="font-mono text-text-primary">{{ getSubscriptionBySite(row.site)?.videos_found || '-' }}</span>
        </template>

        <template #column-videos_enqueued="{ row }">
          <span class="font-mono text-color-success">{{ getSubscriptionBySite(row.site)?.videos_enqueued || '-' }}</span>
        </template>
      </DataTable>
      
      <!-- 最近错误详情 -->
      <div v-if="dashboardData?.recent_errors?.length" class="bg-bg-secondary rounded-lg border border-border-primary">
        <div class="px-4 py-2.5 border-b border-white/5 flex items-center justify-between">
          <span class="text-sm font-medium text-white">最近错误</span>
          <span class="text-xs text-text-tertiary">最近 {{ dashboardData.recent_errors.length }} 条</span>
        </div>
        <div class="divide-y divide-white/5 max-h-80 overflow-y-auto custom-scrollbar">
          <div v-for="(err, idx) in dashboardData.recent_errors" :key="idx" class="px-4 py-2.5 hover:bg-white/[0.02]">
            <div class="flex items-center justify-between text-xs mb-1">
              <div class="flex items-center gap-2">
                <span class="text-color-error font-medium">{{ err.type }}</span>
                <span class="text-text-tertiary">{{ err.site }}</span>
              </div>
              <span class="text-text-tertiary">{{ formatTime(err.time) }}</span>
            </div>
            <a :href="err.url" target="_blank" class="text-xs text-text-tertiary hover:text-color-info truncate mb-1.5 block" :title="err.url">{{ err.url }}</a>
            <details class="text-xs group">
              <summary class="text-text-tertiary cursor-pointer hover:text-text-secondary select-none">
                <span class="group-open:hidden">▶</span>
                <span class="hidden group-open:inline">▼</span>
                {{ getErrorSummary(err.msg) }}
              </summary>
              <pre class="error-stack mt-2 p-3 bg-bg-primary rounded text-text-muted overflow-x-auto whitespace-pre-wrap text-[11px] leading-relaxed max-h-52 overflow-y-auto">{{ err.msg }}</pre>
            </details>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import axios from '../utils/axios'
import StatsCard from '../components/common/StatsCard.vue'
import Card from '../components/common/Card.vue'
import StatusBadge from '../components/common/StatusBadge.vue'

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
  if (status === 'healthy') return 'bg-color-success'
  if (status === 'degraded') return 'bg-color-warning'
  return 'bg-color-error'
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
  if (score >= 80) return 'text-color-success'
  if (score >= 50) return 'text-color-warning'
  return 'text-color-error'
})

const getSuccessRateColor = () => {
  const rate = dashboardData.value?.crawl?.success_rate || 0
  if (rate >= 80) return 'success'
  if (rate >= 50) return 'warning'
  return 'error'
}

const getQueueDepthColor = () => {
  const depth = dashboardData.value?.queues?.total_depth || 0
  if (depth < 100) return 'default'
  if (depth < 500) return 'warning'
  return 'error'
}

const getSiteRateClass = (rate) => {
  if (rate >= 80) return 'text-color-success'
  if (rate >= 50) return 'text-color-warning'
  return 'text-color-error'
}

const getSubscriptionBySite = (siteName) => {
  const subscriptions = dashboardData.value?.subscriptions?.by_site || []
  return subscriptions.find(s => s.site === siteName) || null
}

const formatTime = (isoTime) => {
  if (!isoTime) return '-'
  const date = new Date(isoTime)
  return date.toLocaleTimeString()
}

const getErrorSummary = (msg) => {
  if (!msg) return '点击查看详情'
  const firstLine = msg.split('\n')[0]
  return firstLine.length > 80 ? firstLine.slice(0, 80) + '...' : firstLine
}

onMounted(() => {
  fetchDashboard()
  refreshTimer = setInterval(fetchDashboard, 10000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.monitoring-page {
  font-feature-settings: "tnum";
}

/* 自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar,
.error-stack::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track,
.error-stack::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb,
.error-stack::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover,
.error-stack::-webkit-scrollbar-thumb:hover {
  background: #444;
}

/* Firefox */
.custom-scrollbar,
.error-stack {
  scrollbar-width: thin;
  scrollbar-color: #333 transparent;
}

/* 隐藏 summary 默认箭头 */
details summary::-webkit-details-marker {
  display: none;
}
details summary {
  list-style: none;
}
</style>
