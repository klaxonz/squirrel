<template>
  <div class="scheduled-page flex flex-col h-full bg-background text-foreground">
    <div class="scheduled-shell flex-none px-6 pt-6 pb-3">
      <section class="schedule-hero">
        <div class="schedule-hero__copy">
          <span class="schedule-eyebrow">automation control room</span>
          <h1 class="schedule-hero__title">定时任务管理</h1>
          <p class="schedule-hero__description">统一查看调度器状态、任务负载与执行结果，把“新增任务”和“处理异常”放在同一条操作链里。</p>
        </div>
        <div class="schedule-hero__actions">
          <Button
            @click="showCreateDialog = true"
            size="sm"
            variant="default"
            class="rounded-full shadow-lg shadow-primary/20"
          >
            创建任务
          </Button>
          <Button
            @click="refreshData"
            :disabled="loading"
            size="sm"
            variant="secondary"
            class="rounded-full"
          >
            刷新
          </Button>
        </div>
      </section>

      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4 mt-4">
        <Card class="schedule-stat-card">
          <CardContent class="p-4">
            <p class="schedule-stat-card__label">总任务</p>
            <p class="schedule-stat-card__value text-foreground">{{ statistics.total_tasks }}</p>
          </CardContent>
        </Card>
        <Card class="schedule-stat-card schedule-stat-card--accent">
          <CardContent class="p-4">
            <p class="schedule-stat-card__label">活跃</p>
            <p class="schedule-stat-card__value text-success">{{ statistics.active_tasks }}</p>
          </CardContent>
        </Card>
        <Card class="schedule-stat-card">
          <CardContent class="p-4">
            <p class="schedule-stat-card__label">运行中</p>
            <p class="schedule-stat-card__value text-foreground">{{ statistics.running_tasks }}</p>
          </CardContent>
        </Card>
        <Card class="schedule-stat-card">
          <CardContent class="p-4">
            <p class="schedule-stat-card__label">错误</p>
            <p class="schedule-stat-card__value text-destructive">{{ statistics.error_tasks }}</p>
          </CardContent>
        </Card>
        <Card class="schedule-stat-card schedule-stat-card--muted">
          <CardContent class="p-4">
            <p class="schedule-stat-card__label">今日执行</p>
            <p class="schedule-stat-card__value text-foreground">{{ statistics.today_executions }}</p>
          </CardContent>
        </Card>
      </div>

      <div class="schedule-filter-shell mb-3">
        <div class="schedule-filter-shell__row">
          <div class="schedule-filter-shell__status">
            <div class="schedule-filter-shell__status-copy">
              <span class="schedule-filter-shell__label">调度器</span>
              <Badge :variant="schedulerStatus?.running ? 'secondary' : 'destructive'" class="rounded-full">
                {{ schedulerStatus?.running ? '运行中' : '已停止' }}
              </Badge>
            </div>
            <p class="schedule-filter-shell__hint">
              {{ schedulerStatus?.running ? '任务会按计划持续触发，适合关注异常和负载。' : '调度器已停用，所有计划任务都不会自动触发。' }}
            </p>
          </div>
          <div class="schedule-filter-shell__controls">
            <div class="schedule-inline-actions">
              <span class="schedule-filter-shell__label">切换状态</span>
              <Button
                v-if="!schedulerStatus?.running"
                @click="enableScheduler"
                :disabled="loading"
                size="xs"
                variant="default"
                class="rounded-full"
              >
                启用
              </Button>
              <Button
                v-if="schedulerStatus?.running"
                @click="disableScheduler"
                :disabled="loading"
                size="xs"
                variant="ghost"
                class="rounded-full"
              >
                禁用
              </Button>
            </div>
            <div v-if="hasActiveFilters" class="schedule-filter-shell__active-tag">筛选已生效</div>
          </div>
        </div>
        <div class="schedule-filter-shell__row schedule-filter-shell__row--filters">
          <div class="flex-1 min-w-[220px]">
            <input
              v-model="searchQuery"
              @input="debouncedSearch"
              type="text"
              placeholder="搜索任务、描述或错误..."
              class="schedule-search-input"
            >
          </div>
          <div class="w-32">
            <Select :model-value="statusFilter" @update:model-value="(value) => { statusFilter = value; loadTasks(); }">
              <SelectTrigger class="h-10 text-xs rounded-full border-border/80 bg-background/70">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="w-36">
            <Select :model-value="typeFilter" @update:model-value="(value) => { typeFilter = value; loadTasks(); }">
              <SelectTrigger class="h-10 text-xs rounded-full border-border/80 bg-background/70">
                <SelectValue placeholder="类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in typeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>

    <div class="scheduled-shell flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
      <div class="schedule-table-shell overflow-hidden">
        <table class="w-full">
          <thead class="schedule-table-shell__thead border-b border-border">
            <tr>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-muted-foreground/70 tracking-wider">任务名称</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-muted-foreground/70 tracking-wider">状态</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-muted-foreground/70 tracking-wider">类型</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-muted-foreground/70 tracking-wider">执行间隔</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-muted-foreground/70 tracking-wider">最后执行</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-muted-foreground/70 tracking-wider">下次执行</th>
              <th class="px-3 py-2 text-center text-2xs font-semibold text-muted-foreground/70 tracking-wider">成功/总数</th>
              <th class="px-3 py-2 text-right text-2xs font-semibold text-muted-foreground/70 tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr
              v-for="task in tasks"
              :key="task.id"
              class="schedule-table-shell__row"
            >
              <td class="px-3 py-2">
                <div class="schedule-task-name">{{ task.name }}</div>
                <div v-if="task.description" class="text-2xs text-muted-foreground/70 mt-0.5 leading-5">{{ task.description }}</div>
                <div v-if="task.last_error" class="text-2xs text-destructive mt-0.5" :title="task.last_error">错误: {{ task.last_error }}</div>
              </td>

              <td class="px-3 py-2">
                <Badge :variant="getStatusBadgeVariant(task.status)" class="rounded-full px-2.5 py-1">
                  {{ getStatusText(task.status) }}
                </Badge>
              </td>

              <td class="px-3 py-2">
                <span class="schedule-type-chip">{{ getTypeText(task.task_type) }}</span>
              </td>

              <td class="px-3 py-2">
                <span class="text-2xs text-foreground">{{ task.interval }} {{ getUnitLabel(task.unit) }}</span>
              </td>

              <td class="px-3 py-2">
                <span class="text-2xs text-muted-foreground">{{ formatDateTime(task.last_run_at) || '从未' }}</span>
              </td>

              <td class="px-3 py-2">
                <span class="text-2xs text-muted-foreground">{{ formatDateTime(task.next_run_at) || '未知' }}</span>
              </td>

              <td class="px-3 py-2 text-center">
                <span class="schedule-run-ratio">{{ task.success_count }}/{{ task.run_count }}</span>
              </td>

              <td class="px-3 py-2">
                <div class="flex gap-1 justify-end">
                  <Button
                    v-if="!task.is_legacy"
                    @click="executeTaskNow(task.id)"
                    :disabled="loading"
                    size="xs"
                    variant="secondary"
                    class="rounded-full"
                    title="立即执行"
                  >
                    执行
                  </Button>
                  <Button
                    v-if="!task.is_legacy"
                    @click="editTask(task)"
                    size="xs"
                    variant="ghost"
                    class="rounded-full"
                    title="编辑"
                  >
                    编辑
                  </Button>
                  <Button
                    v-if="!task.is_legacy && task.is_active"
                    @click="disableTask(task.id)"
                    size="xs"
                    variant="ghost"
                    class="rounded-full"
                    title="禁用"
                  >
                    禁用
                  </Button>
                  <Button
                    v-if="!task.is_legacy && !task.is_active"
                    @click="enableTask(task.id)"
                    size="xs"
                    variant="ghost"
                    class="rounded-full"
                    title="启用"
                  >
                    启用
                  </Button>
                  <Button
                    v-if="!task.is_legacy && task.task_type !== 'system'"
                    @click="deleteTask(task.id)"
                    size="xs"
                    variant="destructive"
                    class="rounded-full"
                    title="删除"
                  >
                    删除
                  </Button>
                  <Badge v-if="task.is_legacy" variant="outline" class="rounded-full" title="系统内置任务，不可修改">系统</Badge>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="totalPages > 1" class="flex justify-center mt-6 mb-4">
        <div class="flex items-center gap-2">
          <Button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage <= 1"
            size="sm"
            variant="secondary"
            class="rounded-full"
          >
            上一页
          </Button>
          <div class="px-4 py-2 bg-card border border-border text-foreground text-sm font-medium rounded-lg">
            第 {{ currentPage }} / {{ totalPages }} 页
          </div>
          <Button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            size="sm"
            variant="secondary"
            class="rounded-full"
          >
            下一页
          </Button>
        </div>
      </div>

      <div v-if="tasks.length === 0 && !loading" class="text-center py-16">
        <div class="schedule-empty-state max-w-md mx-auto">
          <ClockIcon class="w-20 h-20 mx-auto mb-4 text-muted-foreground" />
          <h3 class="text-lg font-semibold text-foreground mb-2">暂无定时任务</h3>
          <p class="text-sm text-muted-foreground/70 mb-6">点击下方按钮创建您的第一个定时任务</p>
          <Button
            @click="showCreateDialog = true"
            size="sm"
            variant="default"
            class="rounded-full"
          >
            创建第一个任务
          </Button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-16">
        <div class="schedule-loading-state inline-flex items-center gap-3 px-6 py-4">
          <div class="animate-spin rounded-full h-5 w-5 border-2 border-muted-foreground/30 border-t-destructive"></div>
          <span class="text-sm text-muted-foreground font-medium">加载中...</span>
        </div>
      </div>
    </div>

    <TaskDialog
      v-if="showCreateDialog"
      :task-classes="taskClasses"
      @close="showCreateDialog = false"
      @save="handleCreateTask"
    />

    <TaskDialog
      v-if="editingTask"
      :task="editingTask"
      :task-classes="taskClasses"
      @close="editingTask = null"
      @save="handleUpdateTask"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ClockIcon } from '@heroicons/vue/24/outline'
import TaskDialog from '@/components/dialogs/TaskDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { debounce } from '../utils/debounce'
import { Logger } from '@/utils/logger'
import {
  createTask as apiCreateTask,
  deleteTask as apiDeleteTask,
  disableScheduler as apiDisableScheduler,
  disableTask as apiDisableTask,
  enableScheduler as apiEnableScheduler,
  enableTask as apiEnableTask,
  executeTaskNow as apiExecuteTaskNow,
  getAvailableTaskClasses,
  getSchedulerStatus,
  getScheduledTasks,
  getTaskDetail,
  getTaskStatistics,
  updateTask as apiUpdateTask,
} from '@/api'

// 响应式数据
const schedulerStatus = ref(null)
const statistics = ref({
  total_tasks: 0,
  active_tasks: 0,
  running_tasks: 0,
  error_tasks: 0,
  today_executions: 0
})
const tasks = ref([])
const taskClasses = ref({})
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const searchQuery = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const showCreateDialog = ref(false)

const statusOptions = [
  { value: '', label: '所有状态' },
  { value: 'enabled', label: '启用' },
  { value: 'disabled', label: '禁用' },
  { value: 'running', label: '运行中' },
  { value: 'error', label: '错误' }
]

const typeOptions = [
  { value: '', label: '所有类型' },
  { value: 'system', label: '系统任务' },
  { value: 'user', label: '用户任务' },
  { value: 'plugin', label: '插件任务' }
]

const editingTask = ref(null)

const hasActiveFilters = computed(() => Boolean(searchQuery.value || statusFilter.value || typeFilter.value))

// 防抖搜索
const debouncedSearch = debounce(() => {
  currentPage.value = 1
  loadTasks()
}, 500)

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const [statusResult, statsResult, tasksResult, classesResult] = await Promise.all([
      getSchedulerStatus(),
      getTaskStatistics(),
      loadTasks(),
      getAvailableTaskClasses()
    ])

    if (!statusResult.error) {
      schedulerStatus.value = statusResult.data
    }

    if (!statsResult.error) {
      statistics.value = statsResult.data
    }

    if (!classesResult.error) {
      taskClasses.value = classesResult.data
    }
  } catch (error) {
    Logger.error('Failed to load data', error)
  } finally {
    loading.value = false
  }
}

// 加载任务列表
const loadTasks = async () => {
  try {
    const result = await getScheduledTasks({
      page: currentPage.value,
      page_size: 10,
      search: searchQuery.value || undefined,
      status: statusFilter.value || undefined,
      task_type: typeFilter.value || undefined
    })

    if (!result.error && result.data) {
      tasks.value = result.data.data
      totalPages.value = Math.ceil(result.data.total / 10)
    }
  } catch (error) {
    Logger.error('Failed to load task list', error)
  }
}

// 刷新数据
const refreshData = async () => {
  await loadData()
}

// 分页跳转
const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadTasks()
  }
}

// 创建任务
const handleCreateTask = async (taskData) => {
  const result = await apiCreateTask(taskData)
  if (!result.error) {
    showCreateDialog.value = false
    await refreshData()
  }
}

// 编辑任务
const editTask = (task) => {
  editingTask.value = task
}

// 更新任务
const handleUpdateTask = async (taskData) => {
  const result = await apiUpdateTask(editingTask.value.id, taskData)
  if (!result.error) {
    editingTask.value = null
    await refreshData()
  }
}

// 删除任务
const deleteTask = async (taskId) => {
  const result = await apiDeleteTask(taskId)
  if (!result.error) {
    await refreshData()
  }
}

// 启用任务
const enableTask = async (taskId) => {
  const result = await apiEnableTask(taskId)
  if (!result.error) {
    await refreshData()
  }
}

// 禁用任务
const disableTask = async (taskId) => {
  const result = await apiDisableTask(taskId)
  if (!result.error) {
    await refreshData()
  }
}

// 立即执行任务
const executeTaskNow = async (taskId) => {
  const result = await apiExecuteTaskNow(taskId)
  if (!result.error) {
    setTimeout(() => refreshData(), 1000)
  }
}

// 启用调度器
const enableScheduler = async () => {
  const result = await apiEnableScheduler()
  if (!result.error) {
    schedulerStatus.value.running = true
    await refreshData()
  }
}

// 禁用调度器
const disableScheduler = async () => {
  const result = await apiDisableScheduler()
  if (!result.error) {
    schedulerStatus.value.running = false
    await refreshData()
  }
}

// 工具函数
const getUnitLabel = (unit) => {
  const labels = {
    seconds: '秒',
    minutes: '分钟',
    hours: '小时',
    days: '天'
  }
  return labels[unit] || unit
}

const getStatusBadgeVariant = (status) => {
  const variants = {
    enabled: 'secondary',
    running: 'secondary',
    disabled: 'outline',
    error: 'destructive'
  }
  return variants[status] || 'outline'
}

const getStatusText = (status) => {
  const texts = {
    enabled: '启用',
    disabled: '禁用',
    running: '运行中',
    error: '错误'
  }
  return texts[status] || status
}

const getTypeText = (taskType) => {
  const texts = {
    system: '系统',
    user: '用户',
    plugin: '插件'
  }
  return texts[taskType] || taskType
}

const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return null
  try {
    const date = new Date(dateTimeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (e) {
    return dateTimeStr
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.scheduled-page {
  font-feature-settings: 'tnum';
}

.scheduled-shell {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  width: 100%;
}

.schedule-hero {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 1.5rem;
  border: 1px solid hsl(var(--border) / 0.8);
  border-radius: 1.75rem;
  background:
    radial-gradient(circle at top left, hsl(var(--primary) / 0.16), transparent 34%),
    radial-gradient(circle at bottom right, hsl(var(--accent) / 0.8), transparent 42%),
    linear-gradient(135deg, hsl(var(--card)), hsl(var(--card) / 0.94));
  box-shadow: 0 24px 60px hsl(var(--foreground) / 0.05);
}

.schedule-eyebrow,
.schedule-filter-shell__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: hsl(var(--muted-foreground));
}

.schedule-hero__title {
  margin-top: 0.6rem;
  font-size: clamp(1.85rem, 2vw, 2.5rem);
  line-height: 1.05;
  font-weight: 600;
}

.schedule-hero__description {
  margin-top: 0.75rem;
  max-width: 42rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.7;
  font-size: 0.95rem;
}

.schedule-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-start;
}

.schedule-stat-card,
.schedule-table-shell,
.schedule-empty-state,
.schedule-loading-state,
.schedule-filter-shell {
  border: 1px solid hsl(var(--border) / 0.76);
  background: linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
  box-shadow: 0 18px 46px hsl(var(--foreground) / 0.04);
}

.schedule-stat-card {
  overflow: hidden;
}

.schedule-stat-card--accent {
  background:
    radial-gradient(circle at top left, hsl(var(--primary) / 0.14), transparent 35%),
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
}

.schedule-stat-card--muted {
  background:
    radial-gradient(circle at bottom right, hsl(var(--secondary) / 0.8), transparent 35%),
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
}

.schedule-stat-card__label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: hsl(var(--muted-foreground));
}

.schedule-stat-card__value {
  margin-top: 0.8rem;
  font-size: 1.85rem;
  line-height: 1;
  font-weight: 600;
}

.schedule-filter-shell {
  padding: 1rem;
  border-radius: 1.5rem;
}

.schedule-filter-shell__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.schedule-filter-shell__row + .schedule-filter-shell__row {
  margin-top: 1rem;
}

.schedule-filter-shell__row--filters {
  align-items: stretch;
}

.schedule-filter-shell__status {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.schedule-filter-shell__status-copy {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.schedule-filter-shell__hint {
  color: hsl(var(--muted-foreground));
  font-size: 0.82rem;
}

.schedule-filter-shell__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.85rem;
}

.schedule-inline-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.8rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background) / 0.7);
}

.schedule-filter-shell__active-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.55rem 0.9rem;
  border-radius: 999px;
  background: hsl(var(--warning) / 0.12);
  color: hsl(var(--warning));
  font-size: 0.78rem;
  font-weight: 500;
}

.schedule-search-input {
  width: 100%;
  min-height: 2.75rem;
  padding: 0.7rem 1rem;
  border: 1px solid hsl(var(--border) / 0.85);
  border-radius: 999px;
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--foreground));
  font-size: 0.8rem;
  transition: border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease;
}

.schedule-search-input::placeholder {
  color: hsl(var(--muted-foreground));
}

.schedule-search-input:focus {
  outline: none;
  border-color: hsl(var(--primary) / 0.45);
  box-shadow: 0 0 0 3px hsl(var(--primary) / 0.08);
}

.schedule-table-shell {
  border-radius: 1.6rem;
}

.schedule-table-shell__thead {
  background: linear-gradient(180deg, hsl(var(--background) / 0.96), hsl(var(--card) / 0.92));
}

.schedule-table-shell__row {
  transition: background-color 160ms ease;
}

.schedule-table-shell__row:hover {
  background: hsl(var(--accent) / 0.58);
}

.schedule-task-name {
  font-size: 0.86rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.schedule-type-chip,
.schedule-run-ratio {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 1.85rem;
  padding: 0.2rem 0.75rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
}

.schedule-run-ratio {
  color: hsl(var(--foreground));
}

.schedule-empty-state {
  padding: 2rem;
  border-radius: 1.5rem;
}

.schedule-loading-state {
  border-radius: 999px;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: hsl(var(--border));
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--border));
}

@media (max-width: 767px) {
  .schedule-filter-shell__controls {
    justify-content: flex-start;
  }
}
</style>
