<template>
  <div class="flex flex-col h-full bg-background text-foreground">
    <div class="flex-none px-6 pt-6 pb-3">
      <!-- 标题和操作栏 -->
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-xl font-bold text-foreground">定时任务管理</h1>
        <div class="flex gap-2">
          <Button
            @click="showCreateDialog = true"
            size="sm"
            variant="default"
            class="rounded-full"
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
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">总任务</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ statistics.total_tasks }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">活跃</p>
            <p class="mt-2 text-2xl font-semibold text-emerald-500">{{ statistics.active_tasks }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">运行中</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ statistics.running_tasks }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">错误</p>
            <p class="mt-2 text-2xl font-semibold text-destructive">{{ statistics.error_tasks }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <p class="text-2xs text-muted-foreground/70">今日执行</p>
            <p class="mt-2 text-2xl font-semibold text-foreground">{{ statistics.today_executions }}</p>
          </CardContent>
        </Card>
      </div>

      <!-- 调度器状态和筛选 -->
      <div class="bg-card border border-border rounded-lg p-3 mb-3">
        <div class="flex flex-wrap items-center gap-2">
          <!-- 调度器状态 -->
          <div class="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-full">
            <span class="text-2xs text-muted-foreground/70">调度器</span>
            <Badge :variant="schedulerStatus?.running ? 'secondary' : 'destructive'" class="rounded-full">
              {{ schedulerStatus?.running ? '运行中' : '已停止' }}
            </Badge>
          </div>
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
          <!-- 搜索和过滤 -->
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="searchQuery"
              @input="debouncedSearch"
              type="text"
              placeholder="搜索任务..."
              class="w-full px-3 py-1.5 bg-muted border border-border rounded text-foreground text-2xs placeholder:text-muted-foreground focus:outline-none focus:border-border focus:ring-1 focus:ring-border transition-colors"
            >
          </div>
          <div class="w-28">
            <Select :model-value="statusFilter" @update:model-value="(value) => { statusFilter = value; loadTasks(); }">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="w-32">
            <Select :model-value="typeFilter" @update:model-value="(value) => { typeFilter = value; loadTasks(); }">
              <SelectTrigger class="h-9 text-xs">
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

    <!-- 任务列表 -->
    <div class="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
      <!-- 表格 -->
      <div class="bg-card border border-border rounded-lg overflow-hidden">
        <table class="w-full">
          <thead class="bg-background border-b border-border">
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
              class="hover:bg-muted transition-colors"
            >
              <!-- 任务名称 -->
              <td class="px-3 py-2">
                <div class="text-xs font-medium text-foreground">{{ task.name }}</div>
                <div v-if="task.description" class="text-2xs text-muted-foreground/70 mt-0.5">{{ task.description }}</div>
                <div v-if="task.last_error" class="text-2xs text-destructive mt-0.5" :title="task.last_error">错误: {{ task.last_error }}</div>
              </td>

              <!-- 状态 -->
              <td class="px-3 py-2">
                <Badge :variant="getStatusBadgeVariant(task.status)" class="rounded-full">
                  {{ getStatusText(task.status) }}
                </Badge>
              </td>

              <!-- 类型 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-muted-foreground">{{ getTypeText(task.task_type) }}</span>
              </td>

              <!-- 执行间隔 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-foreground">{{ task.interval }} {{ getUnitLabel(task.unit) }}</span>
              </td>

              <!-- 最后执行 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-muted-foreground">{{ formatDateTime(task.last_run_at) || '从未' }}</span>
              </td>

              <!-- 下次执行 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-muted-foreground">{{ formatDateTime(task.next_run_at) || '未知' }}</span>
              </td>

              <!-- 成功/总数 -->
              <td class="px-3 py-2 text-center">
                <span class="text-2xs text-foreground">{{ task.success_count }}/{{ task.run_count }}</span>
              </td>

              <!-- 操作 -->
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

      <!-- 分页 -->
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

      <!-- 空状态 -->
      <div v-if="tasks.length === 0 && !loading" class="text-center py-16">
        <div class="bg-card border border-border rounded-lg p-8 max-w-md mx-auto">
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

      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-16">
        <div class="inline-flex items-center gap-3 bg-card border border-border rounded-lg px-6 py-4">
          <div class="animate-spin rounded-full h-5 w-5 border-2 border-muted-foreground/30 border-t-destructive"></div>
          <span class="text-sm text-muted-foreground font-medium">加载中...</span>
        </div>
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <TaskDialog
      v-if="showCreateDialog"
      :task-classes="taskClasses"
      @close="showCreateDialog = false"
      @save="handleCreateTask"
    />

    <!-- 编辑任务对话框 -->
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
import { ref, onMounted } from 'vue'
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
</style>
