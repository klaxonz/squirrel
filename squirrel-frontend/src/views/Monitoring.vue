<template>
  <div class="monitoring-page bg-background text-foreground h-screen flex flex-col overflow-hidden">
    <!-- 顶部状态栏 -->
    <div class="shrink-0">
      <div class="toolbar-container pt-6 pb-4">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 class="text-xl font-medium text-foreground">系统监控</h1>
            <p class="text-sm text-muted-foreground">爬取与订阅的实时运行状态</p>
          </div>
          <div class="flex flex-wrap items-center gap-3 text-xs text-muted-foreground/70">
            <div class="flex items-center gap-2 px-3 py-1.5 bg-card rounded-full">
              <Badge :variant="healthBadgeVariant" class="rounded-full" :class="healthBadgeClass">{{ healthStatusText }}</Badge>
              <span class="font-mono" :class="healthScoreClass">{{ dashboardData?.health?.score || 0 }}</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-1.5 bg-card rounded-full">
              <span>更新</span>
              <span class="font-mono">{{ lastUpdateTime || '—' }}</span>
              <button
                @click="refreshData"
                :disabled="loading"
                class="p-1.5 hover:bg-accent rounded transition-colors"
              >
                <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': loading }" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-container py-6 space-y-5 flex-1 flex flex-col min-h-0 overflow-hidden">
      
      <!-- 概览指标 -->
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3 shrink-0">
        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">爬取任务</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ dashboardData?.crawl?.total || 0 }}</p>
            <div class="mt-2 flex gap-3 text-xs text-muted-foreground/70">
              <span><span class="font-mono text-foreground">{{ dashboardData?.crawl?.success || 0 }}</span> 成功</span>
              <span><span class="font-mono" :class="getErrorNumberClass(dashboardData?.crawl?.error || 0)">{{ dashboardData?.crawl?.error || 0 }}</span> 失败</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">成功率</p>
            <p class="mt-2 text-2xl font-semibold" :class="getSiteRateClass(dashboardData?.crawl?.success_rate || 0)">
              {{ dashboardData?.crawl?.success_rate || 0 }}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">发现视频</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ dashboardData?.crawl?.videos_discovered || 0 }}</p>
            <p class="mt-2 text-xs text-muted-foreground/70">
              <span class="font-mono text-foreground">{{ dashboardData?.crawl?.skipped || 0 }}</span> 跳过
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">队列积压</p>
            <p class="mt-2 text-2xl font-semibold" :class="getQueueDepthTextClass(dashboardData?.queues?.total_depth || 0)">
              {{ dashboardData?.queues?.total_depth || 0 }}
            </p>
            <p class="mt-2 text-xs text-muted-foreground/70">
              <span class="font-mono text-foreground">{{ dashboardData?.queues?.total_messages || 0 }}</span> 消息
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">订阅更新</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ dashboardData?.subscriptions?.total || 0 }}</p>
            <div class="mt-2 flex gap-3 text-xs text-muted-foreground/70">
              <span><span class="font-mono text-foreground">{{ dashboardData?.subscriptions?.success || 0 }}</span> 成功</span>
              <span><span class="font-mono" :class="getErrorNumberClass(dashboardData?.subscriptions?.error || 0)">{{ dashboardData?.subscriptions?.error || 0 }}</span> 失败</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">订阅发现</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ dashboardData?.subscriptions?.videos_found || 0 }}</p>
            <p class="mt-2 text-xs text-muted-foreground/70">
              <span class="font-mono text-foreground">{{ dashboardData?.subscriptions?.videos_enqueued || 0 }}</span> 已入队
            </p>
          </CardContent>
        </Card>
      </div>

      <!-- 性能和错误 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3 shrink-0">
        <Card class="p-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-muted-foreground/70">性能指标</span>
            <span class="text-xs text-muted-foreground/70">单位: 秒</span>
          </div>
          <div class="grid grid-cols-4 gap-3 text-center">
            <div>
              <div class="text-lg font-mono text-foreground">{{ dashboardData?.crawl?.avg_duration || 0 }}</div>
              <div class="text-xs text-muted-foreground/70">平均</div>
            </div>
            <div>
              <div class="text-lg font-mono text-foreground">{{ dashboardData?.crawl?.p50_duration || 0 }}</div>
              <div class="text-xs text-muted-foreground/70">P50</div>
            </div>
            <div>
              <div class="text-lg font-mono text-foreground">{{ dashboardData?.crawl?.p95_duration || 0 }}</div>
              <div class="text-xs text-muted-foreground/70">P95</div>
            </div>
            <div>
              <div class="text-lg font-mono text-foreground">{{ dashboardData?.crawl?.max_duration || 0 }}</div>
              <div class="text-xs text-muted-foreground/70">最大</div>
            </div>
          </div>
        </Card>

        <Card class="p-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-muted-foreground/70">错误统计</span>
            <span class="text-sm font-mono" :class="errorTotalClass">{{ dashboardData?.errors?.total || 0 }}</span>
          </div>
          <div v-if="dashboardData?.errors?.by_type?.length" class="flex flex-wrap gap-1.5">
            <Badge
              v-for="error in dashboardData.errors.by_type.slice(0, 8)"
              :key="error.type"
              variant="destructive"
              class="rounded-full"
            >
              {{ `${error.type}: ${error.count}` }}
            </Badge>
          </div>
          <div v-else class="text-xs text-muted-foreground">暂无错误</div>
        </Card>
      </div>
      
      <!-- 站点统计表格 -->
      <div class="shrink-0">
        <Card class="overflow-hidden">
          <div class="px-4 py-2.5 border-b border-border flex items-center justify-between">
            <span class="text-sm font-medium text-foreground">站点统计</span>
            <span class="text-xs text-muted-foreground/70">{{ dashboardData?.crawl?.by_site?.length || 0 }} 个站点</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[1100px] text-sm">
              <thead class="bg-card">
                <tr class="border-b border-border text-2xs text-muted-foreground/70">
                  <th class="px-3 py-2 text-left font-medium">站点</th>
                  <th class="px-3 py-2 text-right font-medium">成功率</th>
                  <th class="px-3 py-2 text-right font-medium">成功</th>
                  <th class="px-3 py-2 text-right font-medium">失败</th>
                  <th class="px-3 py-2 text-right font-medium">跳过</th>
                  <th class="px-3 py-2 text-right font-medium">发现</th>
                  <th class="px-3 py-2 text-right font-medium">队列</th>
                  <th class="px-3 py-2 text-right font-medium">平均耗时</th>
                  <th class="px-3 py-2 text-right font-medium">P95耗时</th>
                  <th class="px-3 py-2 text-right font-medium">订阅发现</th>
                  <th class="px-3 py-2 text-right font-medium">已入队</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border">
                <tr
                  v-for="row in (dashboardData?.crawl?.by_site || [])"
                  :key="row.site"
                  class="hover:bg-accent transition-colors"
                >
                  <td class="px-3 py-2">
                    <div class="flex items-center gap-2">
                      <span class="w-6 h-6 rounded bg-muted flex items-center justify-center text-2xs font-bold uppercase text-muted-foreground">{{ row.site.slice(0, 2) }}</span>
                      <span class="font-medium text-foreground">{{ row.site }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono" :class="getSiteRateClass(row.success_rate)">{{ row.success_rate }}%</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground">{{ row.success }}</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono" :class="getErrorNumberClass(row.error)">{{ row.error }}</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground/70">{{ row.skipped }}</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground">{{ row.videos }}</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono" :class="getQueueDepthTextClass(row.queue_depth)">{{ row.queue_depth || 0 }}</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground">{{ row.avg_duration || '-' }}s</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground">{{ row.p95_duration || '-' }}s</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground">{{ getSubscriptionBySite(row.site)?.videos_found || '-' }}</span>
                  </td>
                  <td class="px-3 py-2 text-right">
                    <span class="font-mono text-muted-foreground">{{ getSubscriptionBySite(row.site)?.videos_enqueued || '-' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      
      <!-- 最近错误详情 -->
      <Card v-if="dashboardData?.recent_errors?.length" class="overflow-hidden flex flex-col flex-1 min-h-0">
        <div class="px-4 py-2.5 border-b border-border flex items-center justify-between">
          <span class="text-sm font-medium text-foreground">最近错误</span>
          <span class="text-xs text-muted-foreground/70">最近 {{ dashboardData.recent_errors.length }} 条</span>
        </div>
        <div class="divide-y divide-border flex-1 min-h-0 overflow-y-auto scrollbar-hide">
          <div v-for="(err, idx) in dashboardData.recent_errors" :key="idx" class="px-4 py-2.5 hover:bg-accent">
            <div class="flex items-center justify-between text-xs mb-1">
              <div class="flex items-center gap-2">
                <Badge variant="destructive" class="rounded-full">{{ err.type }}</Badge>
                <span class="text-muted-foreground/70">{{ err.site }}</span>
              </div>
              <span class="text-muted-foreground/70">{{ formatTime(err.time) }}</span>
            </div>
            <a :href="err.url" target="_blank" class="text-xs text-muted-foreground/70 hover:text-muted-foreground truncate mb-1.5 block" :title="err.url">{{ err.url }}</a>
            <details class="text-xs group">
              <summary class="text-muted-foreground/70 cursor-pointer hover:text-muted-foreground select-none">
                <span class="group-open:hidden">▶</span>
                <span class="hidden group-open:inline">▼</span>
                {{ getErrorSummary(err.msg) }}
              </summary>
              <pre class="error-stack mt-2 p-3 bg-card rounded text-muted-foreground overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed max-h-52 overflow-y-auto scrollbar-hide">{{ err.msg }}</pre>
            </details>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import { Logger } from '@/utils/logger'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { getDashboard } from '@/api'

const loading = ref(false)
const dashboardData = ref(null)
const lastUpdateTime = ref('')
let refreshTimer = null

const fetchDashboard = async () => {
  loading.value = true
  try {
    const { data, error } = await getDashboard()
    if (error) {
      Logger.error('Failed to fetch dashboard', error)
      return
    }

    dashboardData.value = data
    lastUpdateTime.value = new Date().toLocaleTimeString()
  } catch (error) {
    Logger.error('Failed to fetch dashboard', error)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchDashboard()
}

const siteTableColumns = [
  { key: 'site', label: '站点', align: 'left' },
  { key: 'success_rate', label: '成功率', align: 'right' },
  { key: 'success', label: '成功', align: 'right' },
  { key: 'error', label: '失败', align: 'right' },
  { key: 'skipped', label: '跳过', align: 'right' },
  { key: 'videos', label: '发现', align: 'right' },
  { key: 'queue_depth', label: '队列', align: 'right' },
  { key: 'avg_duration', label: '平均耗时', align: 'right' },
  { key: 'p95_duration', label: 'P95耗时', align: 'right' },
  { key: 'videos_found', label: '订阅发现', align: 'right' },
  { key: 'videos_enqueued', label: '已入队', align: 'right' }
]

// 健康状态
const healthBadgeVariant = computed(() => {
  const status = dashboardData.value?.health?.status
  if (status === 'critical') return 'destructive'
  if (status === 'degraded') return 'outline'
  return 'secondary'
})

const healthBadgeClass = computed(() => {
  const status = dashboardData.value?.health?.status
  if (status === 'degraded') return 'border-amber-500/40 text-amber-500'
  return ''
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
  if (score >= 80) return 'text-foreground'
  if (score >= 50) return 'text-amber-500'
  return 'text-destructive'
})

const getSuccessRateColor = () => {
  const rate = dashboardData.value?.crawl?.success_rate || 0
  if (rate >= 80) return 'default'
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
  if (rate >= 80) return 'text-foreground'
  if (rate >= 50) return 'text-amber-500'
  return 'text-destructive'
}

const getQueueDepthTextClass = (value) => {
  const depth = Number(value) || 0
  if (depth > 100) return 'text-destructive'
  if (depth > 50) return 'text-amber-500'
  return 'text-muted-foreground'
}

const getErrorNumberClass = (value) => {
  return Number(value) > 0 ? 'text-destructive' : 'text-muted-foreground'
}

const errorTotalClass = computed(() => {
  const total = dashboardData.value?.errors?.total || 0
  return total > 0 ? 'text-destructive' : 'text-muted-foreground'
})

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

/* 隐藏 summary 默认箭头 */
details summary::-webkit-details-marker {
  display: none;
}
details summary {
  list-style: none;
}
</style>
