<template>
  <div class="monitoring-page bg-background text-foreground h-screen flex flex-col overflow-hidden">
    <div class="shrink-0">
      <div class="toolbar-container pt-4 pb-4">
        <PageHeader
          title="系统监控"
          description="把爬取、订阅、队列与错误流收拢到同一个运行视图，方便快速判断现在是该扩容、排障，还是继续推进更新。"
        >
          <template #actions>
            <div class="monitor-hero__pill">
              <span class="monitor-hero__label">健康状态</span>
              <Badge :variant="healthBadgeVariant" class="monitor-hero__badge" :class="healthBadgeClass">{{ healthStatusText }}</Badge>
              <span class="font-mono text-lg" :class="healthScoreClass">{{ dashboardData?.health?.score || 0 }}</span>
            </div>
            <div class="monitor-hero__pill">
              <span class="monitor-hero__label">刷新节奏</span>
              <span class="font-mono text-sm text-foreground">10s</span>
              <span class="monitor-hero__divider"></span>
              <span class="monitor-hero__label">最近更新</span>
              <span class="font-mono text-sm text-foreground">{{ lastUpdateTime || '—' }}</span>
            </div>
            <Button
              @click="refreshData"
              :disabled="loading"
              size="sm"
              class="monitor-refresh"
            >
              <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': loading }" />
              <span>{{ loading ? '同步中' : '立即刷新' }}</span>
            </Button>
          </template>
        </PageHeader>
      </div>
    </div>

    <div class="content-container py-5 space-y-4 flex-1 flex flex-col min-h-0 overflow-hidden">
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3 shrink-0">
        <Card class="monitor-metric-card monitor-metric-card--warm">
          <CardContent class="p-3.5">
            <p class="monitor-metric-card__label">爬取任务</p>
            <p class="monitor-metric-card__value">{{ dashboardData?.crawl?.total || 0 }}</p>
            <div class="monitor-metric-card__meta">
              <span><span class="font-mono text-foreground">{{ dashboardData?.crawl?.success || 0 }}</span> 成功</span>
              <span><span class="font-mono" :class="getErrorNumberClass(dashboardData?.crawl?.error || 0)">{{ dashboardData?.crawl?.error || 0 }}</span> 失败</span>
            </div>
          </CardContent>
        </Card>

        <Card class="monitor-metric-card">
          <CardContent class="p-3.5">
            <p class="monitor-metric-card__label">成功率</p>
            <p class="monitor-metric-card__value" :class="getSiteRateClass(dashboardData?.crawl?.success_rate || 0)">
              {{ dashboardData?.crawl?.success_rate || 0 }}%
            </p>
          </CardContent>
        </Card>

        <Card class="monitor-metric-card">
          <CardContent class="p-3.5">
            <p class="monitor-metric-card__label">发现视频</p>
            <p class="monitor-metric-card__value text-foreground">{{ dashboardData?.crawl?.videos_discovered || 0 }}</p>
            <p class="monitor-metric-card__meta">
              <span class="font-mono text-foreground">{{ dashboardData?.crawl?.skipped || 0 }}</span> 跳过
            </p>
          </CardContent>
        </Card>

        <Card class="monitor-metric-card">
          <CardContent class="p-3.5">
            <p class="monitor-metric-card__label">队列积压</p>
            <p class="monitor-metric-card__value" :class="getQueueDepthTextClass(dashboardData?.queues?.total_depth || 0)">
              {{ dashboardData?.queues?.total_depth || 0 }}
            </p>
            <p class="monitor-metric-card__meta">
              <span class="font-mono text-foreground">{{ dashboardData?.queues?.total_messages || 0 }}</span> 消息
            </p>
          </CardContent>
        </Card>

        <Card class="monitor-metric-card">
          <CardContent class="p-3.5">
            <p class="monitor-metric-card__label">订阅更新</p>
            <p class="monitor-metric-card__value text-foreground">{{ dashboardData?.subscriptions?.total || 0 }}</p>
            <div class="monitor-metric-card__meta">
              <span><span class="font-mono text-foreground">{{ dashboardData?.subscriptions?.success || 0 }}</span> 成功</span>
              <span><span class="font-mono" :class="getErrorNumberClass(dashboardData?.subscriptions?.error || 0)">{{ dashboardData?.subscriptions?.error || 0 }}</span> 失败</span>
            </div>
          </CardContent>
        </Card>

        <Card class="monitor-metric-card monitor-metric-card--ink">
          <CardContent class="p-3.5">
            <p class="monitor-metric-card__label">订阅发现</p>
            <p class="monitor-metric-card__value text-foreground">{{ dashboardData?.subscriptions?.videos_found || 0 }}</p>
            <p class="monitor-metric-card__meta">
              <span class="font-mono text-foreground">{{ dashboardData?.subscriptions?.videos_enqueued || 0 }}</span> 已入队
            </p>
          </CardContent>
        </Card>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3 shrink-0">
        <Card class="monitor-panel">
          <div class="monitor-panel__header">
            <div>
              <span class="monitor-panel__eyebrow">runtime latency</span>
              <h2 class="monitor-panel__title">性能指标</h2>
            </div>
            <span class="monitor-panel__caption">单位: 秒</span>
          </div>
          <div class="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
            <div class="monitor-stat-tile">
              <div class="monitor-stat-tile__value">{{ dashboardData?.crawl?.avg_duration || 0 }}</div>
              <div class="monitor-stat-tile__label">平均</div>
            </div>
            <div class="monitor-stat-tile">
              <div class="monitor-stat-tile__value">{{ dashboardData?.crawl?.p50_duration || 0 }}</div>
              <div class="monitor-stat-tile__label">P50</div>
            </div>
            <div class="monitor-stat-tile">
              <div class="monitor-stat-tile__value">{{ dashboardData?.crawl?.p95_duration || 0 }}</div>
              <div class="monitor-stat-tile__label">P95</div>
            </div>
            <div class="monitor-stat-tile">
              <div class="monitor-stat-tile__value">{{ dashboardData?.crawl?.max_duration || 0 }}</div>
              <div class="monitor-stat-tile__label">最大</div>
            </div>
          </div>
        </Card>

        <Card class="monitor-panel">
          <div class="monitor-panel__header">
            <div>
              <span class="monitor-panel__eyebrow">error pressure</span>
              <h2 class="monitor-panel__title">错误统计</h2>
            </div>
            <span class="text-sm font-mono" :class="errorTotalClass">{{ dashboardData?.errors?.total || 0 }}</span>
          </div>
          <div v-if="dashboardData?.errors?.by_type?.length" class="flex flex-wrap gap-2">
            <Badge
              v-for="error in dashboardData.errors.by_type.slice(0, 8)"
              :key="error.type"
              variant="destructive"
              class="rounded-md px-2 py-0.5"
            >
              {{ `${error.type}: ${error.count}` }}
            </Badge>
          </div>
          <div v-else class="monitor-panel__caption">暂无错误</div>
        </Card>
      </div>

      <div class="shrink-0">
        <Card class="monitor-table-card overflow-hidden">
          <div class="monitor-table-card__header">
            <div>
              <span class="monitor-panel__eyebrow">site by site</span>
              <h2 class="monitor-panel__title">站点统计</h2>
            </div>
            <span class="monitor-panel__caption">{{ dashboardData?.crawl?.by_site?.length || 0 }} 个站点</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[1100px] text-sm">
              <thead class="monitor-table-card__thead">
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
                  class="monitor-table-card__row"
                >
                  <td class="px-3 py-2">
                    <div class="flex items-center gap-3">
                      <span class="monitor-site-mark">{{ row.site.slice(0, 2) }}</span>
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

      <Card v-if="dashboardData?.recent_errors?.length" class="monitor-error-card overflow-hidden flex flex-col flex-1 min-h-0">
        <div class="monitor-table-card__header">
          <div>
            <span class="monitor-panel__eyebrow">latest incidents</span>
            <h2 class="monitor-panel__title">最近错误</h2>
          </div>
          <span class="monitor-panel__caption">最近 {{ dashboardData.recent_errors.length }} 条</span>
        </div>
        <div class="divide-y divide-border flex-1 min-h-0 overflow-y-auto scrollbar-hide">
          <div v-for="(err, idx) in dashboardData.recent_errors" :key="idx" class="monitor-error-item">
            <div class="flex items-center justify-between text-xs mb-1">
              <div class="flex items-center gap-2">
                <Badge variant="destructive" class="rounded-md px-2 py-0.5">{{ err.type }}</Badge>
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
              <pre class="error-stack mt-2 rounded-lg border border-border/70 bg-card/80 p-3 text-xs leading-relaxed text-muted-foreground overflow-x-auto whitespace-pre-wrap max-h-52 overflow-y-auto scrollbar-hide">{{ err.msg }}</pre>
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
import PageHeader from '@/components/layout/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
  if (status === 'degraded') return 'border-warning/40 bg-warning/10 text-warning'
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
  if (score >= 50) return 'text-warning'
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
  if (rate >= 50) return 'text-warning'
  return 'text-destructive'
}

const getQueueDepthTextClass = (value) => {
  const depth = Number(value) || 0
  if (depth > 100) return 'text-destructive'
  if (depth > 50) return 'text-warning'
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

.monitor-panel__eyebrow {
  display: inline-flex;
  align-items: center;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground));
}

.monitor-hero__pill {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.75rem;
  border-radius: 0.625rem;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background));
}

.monitor-hero__label,
.monitor-panel__caption {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.monitor-hero__divider {
  width: 1px;
  height: 0.875rem;
  background: hsl(var(--border));
}

.monitor-refresh {
  gap: 0.5rem;
  box-shadow: none;
}

.monitor-metric-card {
  border-color: hsl(var(--border) / 0.7);
  background:
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.92));
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.035);
}

.monitor-metric-card--warm {
  background:
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.92)),
    radial-gradient(circle at top left, hsl(var(--primary) / 0.14), transparent 38%);
}

.monitor-metric-card--ink {
  background:
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.9)),
    radial-gradient(circle at bottom right, hsl(var(--secondary) / 0.9), transparent 34%);
}

.monitor-metric-card__label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: hsl(var(--muted-foreground));
}

.monitor-metric-card__value {
  margin-top: 0.6rem;
  font-size: 1.65rem;
  line-height: 1;
  font-weight: 600;
}

.monitor-metric-card__meta {
  margin-top: 0.65rem;
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.monitor-panel,
.monitor-table-card,
.monitor-error-card {
  border-color: hsl(var(--border) / 0.72);
  background:
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.035);
}

.monitor-panel {
  padding: 0.9rem;
}

.monitor-panel__header,
.monitor-table-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
}

.monitor-panel__title {
  margin-top: 0.3rem;
  font-size: 0.95rem;
  font-weight: 600;
}

.monitor-stat-tile {
  padding: 0.8rem 0.7rem;
  border-radius: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.7);
  background: hsl(var(--background) / 0.72);
}

.monitor-stat-tile__value {
  font-size: 1.05rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.monitor-stat-tile__label {
  margin-top: 0.35rem;
  font-size: 0.72rem;
  color: hsl(var(--muted-foreground));
}

.monitor-table-card__header {
  padding: 0.9rem 0.9rem 0.8rem;
  margin-bottom: 0;
  border-bottom: 1px solid hsl(var(--border));
}

.monitor-table-card__thead {
  background:
    linear-gradient(180deg, hsl(var(--background) / 0.95), hsl(var(--card) / 0.88));
}

.monitor-table-card__row {
  transition: background-color 160ms ease;
}

.monitor-table-card__row:hover {
  background: hsl(var(--accent) / 0.65);
}

.monitor-site-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.5rem;
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
}

.monitor-error-item {
  padding: 0.8rem 0.9rem;
  transition: background-color 160ms ease;
}

.monitor-error-item:hover {
  background: hsl(var(--accent) / 0.6);
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
