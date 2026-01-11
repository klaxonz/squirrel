<template>
  <div class="flex flex-col h-full bg-bg-primary text-text-primary">
    <div class="flex-none px-6 pt-6 pb-3">
      <!-- 标题和操作栏 -->
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-xl font-bold text-text-primary">定时任务管理</h1>
        <div class="flex gap-2">
          <Button
            @click="showCreateDialog = true"
            size="sm"
            shape="pill"
            variant="primary"
          >
            创建任务
          </Button>
          <Button
            @click="refreshData"
            :disabled="loading"
            size="sm"
            shape="pill"
            variant="secondary"
          >
            刷新
          </Button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <StatsCard
          title="总任务"
          :value="statistics.total_tasks"
          :hover-effect="true"
        />
        <StatsCard
          title="活跃"
          :value="statistics.active_tasks"
          value-color="success"
          :hover-effect="true"
        />
        <StatsCard
          title="运行中"
          :value="statistics.running_tasks"
          :hover-effect="true"
        />
        <StatsCard
          title="错误"
          :value="statistics.error_tasks"
          value-color="error"
          :hover-effect="true"
        />
        <StatsCard
          title="今日执行"
          :value="statistics.today_executions"
          :hover-effect="true"
        />
      </div>

      <!-- 调度器状态和筛选 -->
      <div class="bg-bg-secondary border border-border-primary rounded-lg p-3 mb-3">
        <div class="flex flex-wrap items-center gap-2">
          <!-- 调度器状态 -->
          <div class="flex items-center gap-2 px-3 py-1.5 bg-bg-elevated rounded-full">
            <span class="text-2xs text-text-tertiary">调度器</span>
            <StatusBadge
              :variant="schedulerStatus?.running ? 'success' : 'error'"
              size="xs"
              class="border-0"
              :label="schedulerStatus?.running ? '运行中' : '已停止'"
            />
          </div>
          <Button
            v-if="!schedulerStatus?.running"
            @click="enableScheduler"
            :disabled="loading"
            size="xs"
            shape="pill"
            variant="primary"
          >
            启用
          </Button>
          <Button
            v-if="schedulerStatus?.running"
            @click="disableScheduler"
            :disabled="loading"
            size="xs"
            shape="pill"
            variant="ghost"
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
              class="w-full px-3 py-1.5 bg-bg-elevated border border-border-secondary rounded text-text-primary text-2xs placeholder-text-muted focus:outline-none focus:border-border-hover focus:ring-1 focus:ring-border-hover transition-colors"
            >
          </div>
          <div class="w-28">
            <Select
              size="sm"
              :model-value="statusFilter"
              :options="statusOptions"
              @update:model-value="(value) => { statusFilter = value; loadTasks(); }"
            />
          </div>
          <div class="w-32">
            <Select
              size="sm"
              :model-value="typeFilter"
              :options="typeOptions"
              @update:model-value="(value) => { typeFilter = value; loadTasks(); }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
      <!-- 表格 -->
      <div class="bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
        <table class="w-full">
          <thead class="bg-bg-primary border-b border-border-primary">
            <tr>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-text-tertiary tracking-wider">任务名称</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-text-tertiary tracking-wider">状态</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-text-tertiary tracking-wider">类型</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-text-tertiary tracking-wider">执行间隔</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-text-tertiary tracking-wider">最后执行</th>
              <th class="px-3 py-2 text-left text-2xs font-semibold text-text-tertiary tracking-wider">下次执行</th>
              <th class="px-3 py-2 text-center text-2xs font-semibold text-text-tertiary tracking-wider">成功/总数</th>
              <th class="px-3 py-2 text-right text-2xs font-semibold text-text-tertiary tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-primary">
            <tr
              v-for="task in tasks"
              :key="task.id"
              class="hover:bg-bg-elevated transition-colors"
            >
              <!-- 任务名称 -->
              <td class="px-3 py-2">
                <div class="text-xs font-medium text-text-primary">{{ task.name }}</div>
                <div v-if="task.description" class="text-2xs text-text-tertiary mt-0.5">{{ task.description }}</div>
                <div v-if="task.last_error" class="text-2xs text-color-error mt-0.5" :title="task.last_error">错误: {{ task.last_error }}</div>
              </td>

              <!-- 状态 -->
              <td class="px-3 py-2">
                <StatusBadge
                  size="xs"
                  :show-dot="false"
                  :variant="getStatusVariant(task.status)"
                  :label="getStatusText(task.status)"
                  class="border-0"
                />
              </td>

              <!-- 类型 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-text-secondary">{{ getTypeText(task.task_type) }}</span>
              </td>

              <!-- 执行间隔 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-text-primary">{{ task.interval }} {{ getUnitLabel(task.unit) }}</span>
              </td>

              <!-- 最后执行 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-text-secondary">{{ formatDateTime(task.last_run_at) || '从未' }}</span>
              </td>

              <!-- 下次执行 -->
              <td class="px-3 py-2">
                <span class="text-2xs text-text-secondary">{{ formatDateTime(task.next_run_at) || '未知' }}</span>
              </td>

              <!-- 成功/总数 -->
              <td class="px-3 py-2 text-center">
                <span class="text-2xs text-text-primary">{{ task.success_count }}/{{ task.run_count }}</span>
              </td>

              <!-- 操作 -->
              <td class="px-3 py-2">
                <div class="flex gap-1 justify-end">
                  <Button
                    v-if="!task.is_legacy"
                    @click="executeTaskNow(task.id)"
                    :disabled="loading"
                    size="xs"
                    shape="pill"
                    variant="secondary"
                    title="立即执行"
                  >
                    执行
                  </Button>
                  <Button
                    v-if="!task.is_legacy"
                    @click="editTask(task)"
                    size="xs"
                    shape="pill"
                    variant="ghost"
                    title="编辑"
                  >
                    编辑
                  </Button>
                  <Button
                    v-if="!task.is_legacy && task.is_active"
                    @click="disableTask(task.id)"
                    size="xs"
                    shape="pill"
                    variant="ghost"
                    title="禁用"
                  >
                    禁用
                  </Button>
                  <Button
                    v-if="!task.is_legacy && !task.is_active"
                    @click="enableTask(task.id)"
                    size="xs"
                    shape="pill"
                    variant="ghost"
                    title="启用"
                  >
                    启用
                  </Button>
                  <Button
                     v-if="!task.is_legacy && task.task_type !== 'system'"
                     @click="deleteTask(task.id)"
                     size="xs"
                     shape="pill"
                     variant="danger"
                     title="删除"
                   >
                     删除
                   </Button>
                  <StatusBadge
                    v-if="task.is_legacy"
                    size="xs"
                    :show-dot="false"
                    label="系统"
                    class="border-0"
                    title="系统内置任务，不可修改"
                  />
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
            shape="pill"
            variant="secondary"
          >
            上一页
          </Button>
          <div class="px-4 py-2 bg-bg-secondary border border-border-secondary text-text-primary text-sm font-medium rounded-lg">
            第 {{ currentPage }} / {{ totalPages }} 页
          </div>
          <Button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            size="sm"
            shape="pill"
            variant="secondary"
          >
            下一页
          </Button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="tasks.length === 0 && !loading" class="text-center py-16">
        <div class="bg-bg-secondary border border-border-primary rounded-lg p-8 max-w-md mx-auto">
          <ClockIcon class="w-20 h-20 mx-auto mb-4 text-text-muted" />
          <h3 class="text-lg font-semibold text-text-primary mb-2">暂无定时任务</h3>
          <p class="text-sm text-text-tertiary mb-6">点击下方按钮创建您的第一个定时任务</p>
          <Button
            @click="showCreateDialog = true"
            size="sm"
            shape="pill"
            variant="primary"
          >
            创建第一个任务
          </Button>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-16">
        <div class="inline-flex items-center gap-3 bg-bg-secondary border border-border-primary rounded-lg px-6 py-4">
          <div class="animate-spin rounded-full h-5 w-5 border-2 border-text-muted border-t-color-error"></div>
          <span class="text-sm text-text-secondary font-medium">加载中...</span>
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
import { useSchedulerApi } from '../composables/useSchedulerApi'
import TaskDialog from '../components/TaskDialog.vue'
import Button from '../components/common/Button.vue'
import StatsCard from '../components/common/StatsCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import Select from '../components/common/Select.vue'
import { debounce } from '../utils/debounce'

const {
  getSchedulerStatus,
  getTaskStatistics,
  getScheduledTasks,
  getTaskDetail,
  createTask: apiCreateTask,
  updateTask: apiUpdateTask,
  deleteTask: apiDeleteTask,
  enableTask: apiEnableTask,
  disableTask: apiDisableTask,
  executeTaskNow: apiExecuteTaskNow,
  getAvailableTaskClasses,
  enableScheduler: apiEnableScheduler,
  disableScheduler: apiDisableScheduler
} = useSchedulerApi()

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

    if (statusResult.success) {
      schedulerStatus.value = statusResult.data
    }

    if (statsResult.success) {
      statistics.value = statsResult.data
    }

    if (classesResult.success) {
      taskClasses.value = classesResult.data
    }
  } catch (error) {
    console.error('加载数据失败:', error)
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

    if (result.success) {
      tasks.value = result.data.data
      totalPages.value = Math.ceil(result.data.total / 10)
    }
  } catch (error) {
    console.error('加载任务列表失败:', error)
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
  if (result.success) {
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
  if (result.success) {
    editingTask.value = null
    await refreshData()
  }
}

// 删除任务
const deleteTask = async (taskId) => {
  const result = await apiDeleteTask(taskId)
  if (result.success) {
    await refreshData()
  }
}

// 启用任务
const enableTask = async (taskId) => {
  const result = await apiEnableTask(taskId)
  if (result.success) {
    await refreshData()
  }
}

// 禁用任务
const disableTask = async (taskId) => {
  const result = await apiDisableTask(taskId)
  if (result.success) {
    await refreshData()
  }
}

// 立即执行任务
const executeTaskNow = async (taskId) => {
  const result = await apiExecuteTaskNow(taskId)
  if (result.success) {
    setTimeout(() => refreshData(), 1000)
  }
}

// 启用调度器
const enableScheduler = async () => {
  const result = await apiEnableScheduler()
  if (result.success) {
    schedulerStatus.value.running = true
    await refreshData()
  }
}

// 禁用调度器
const disableScheduler = async () => {
  const result = await apiDisableScheduler()
  if (result.success) {
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

const getStatusVariant = (status) => {
  const variants = {
    enabled: 'success',
    running: 'success',
    disabled: 'default',
    error: 'error'
  }
  return variants[status] || 'default'
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
  background: var(--border-secondary);
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: var(--border-hover);
}
</style>
