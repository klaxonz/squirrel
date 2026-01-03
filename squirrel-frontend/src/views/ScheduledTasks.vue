<template>
  <div class="flex flex-col h-full">
    <div class="flex-none px-4 pt-2 pb-3">
      <!-- 标题和操作栏 -->
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-xl font-semibold">定时任务管理</h1>
        <div class="flex space-x-2">
          <button
            @click="showCreateDialog = true"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
          >
            创建任务
          </button>
          <button
            @click="refreshData"
            :disabled="loading"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
          >
            刷新
          </button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
        <div class="bg-[#1f1f1f] rounded-xl p-4">
          <div class="text-2xl font-bold text-white">{{ statistics.total_tasks }}</div>
          <div class="text-sm text-gray-400">总任务数</div>
        </div>
        <div class="bg-[#1f1f1f] rounded-xl p-4">
          <div class="text-2xl font-bold text-green-500">{{ statistics.active_tasks }}</div>
          <div class="text-sm text-gray-400">活跃任务</div>
        </div>
        <div class="bg-[#1f1f1f] rounded-xl p-4">
          <div class="text-2xl font-bold text-blue-500">{{ statistics.running_tasks }}</div>
          <div class="text-sm text-gray-400">运行中</div>
        </div>
        <div class="bg-[#1f1f1f] rounded-xl p-4">
          <div class="text-2xl font-bold text-red-500">{{ statistics.error_tasks }}</div>
          <div class="text-sm text-gray-400">错误任务</div>
        </div>
        <div class="bg-[#1f1f1f] rounded-xl p-4">
          <div class="text-2xl font-bold text-yellow-500">{{ statistics.today_executions }}</div>
          <div class="text-sm text-gray-400">今日执行</div>
        </div>
      </div>

      <!-- 调度器状态控制 -->
      <div class="bg-[#1f1f1f] rounded-xl p-4 mb-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="flex items-center">
              <div
                class="w-3 h-3 rounded-full mr-2"
                :class="schedulerStatus?.running ? 'bg-green-500' : 'bg-red-500'"
              ></div>
              <span class="text-sm font-medium">
                调度器状态: {{ schedulerStatus?.running ? '运行中' : '已停止' }}
              </span>
            </div>
          </div>
          <div class="flex space-x-2">
            <button
              v-if="!schedulerStatus?.running"
              @click="enableScheduler"
              :disabled="loading"
              class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
            >
              启用调度器
            </button>
            <button
              v-if="schedulerStatus?.running"
              @click="disableScheduler"
              :disabled="loading"
              class="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
            >
              禁用调度器
            </button>
          </div>
        </div>
      </div>

      <!-- 搜索和过滤 -->
      <div class="flex flex-wrap gap-2 mb-4">
        <input
          v-model="searchQuery"
          @input="debouncedSearch"
          type="text"
          placeholder="搜索任务..."
          class="px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
        >
        <select
          v-model="statusFilter"
          @change="loadTasks"
          class="px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
        >
          <option value="">所有状态</option>
          <option value="enabled">启用</option>
          <option value="disabled">禁用</option>
          <option value="running">运行中</option>
          <option value="error">错误</option>
        </select>
        <select
          v-model="typeFilter"
          @change="loadTasks"
          class="px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
        >
          <option value="">所有类型</option>
          <option value="system">系统任务</option>
          <option value="user">用户任务</option>
          <option value="plugin">插件任务</option>
        </select>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="flex-1 overflow-y-auto px-4">
      <div class="space-y-3">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="bg-[#1f1f1f] hover:bg-[#272727] transition-colors duration-200 rounded-xl overflow-hidden"
        >
          <div class="p-4">
            <div class="flex items-start justify-between mb-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center space-x-2 mb-1">
                  <h3 class="text-lg font-semibold text-white">{{ task.name }}</h3>
                  <span
                    class="px-2 py-1 rounded text-xs"
                    :class="getStatusBadgeClass(task.status)"
                  >
                    {{ getStatusText(task.status) }}
                  </span>
                  <span
                    class="px-2 py-1 rounded text-xs bg-gray-600 text-white"
                  >
                    {{ getTypeText(task.task_type) }}
                  </span>
                </div>
                <p v-if="task.description" class="text-sm text-gray-400 mb-2">{{ task.description }}</p>
              </div>
              <div class="flex space-x-2 ml-4">
                <button
                  v-if="!task.is_legacy"
                  @click="executeTaskNow(task.id)"
                  :disabled="loading"
                  class="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
                  title="立即执行"
                >
                  执行
                </button>
                <button
                  v-if="!task.is_legacy"
                  @click="editTask(task)"
                  class="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded transition-colors"
                  title="编辑"
                >
                  编辑
                </button>
                <button
                  v-if="!task.is_legacy && task.is_active"
                  @click="disableTask(task.id)"
                  class="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white text-sm rounded transition-colors"
                  title="禁用"
                >
                  禁用
                </button>
                <button
                  v-if="!task.is_legacy && !task.is_active"
                  @click="enableTask(task.id)"
                  class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
                  title="启用"
                >
                  启用
                </button>
                <button
                  v-if="!task.is_legacy"
                  @click="deleteTask(task.id)"
                  class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                  title="删除"
                >
                  删除
                </button>
                <span
                  v-if="task.is_legacy"
                  class="px-3 py-1 bg-gray-700 text-gray-400 text-sm rounded"
                  title="系统内置任务，不可修改"
                >
                  系统任务
                </span>
              </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
              <div>
                <span class="text-gray-400">执行间隔:</span>
                <span class="text-white ml-2">{{ task.interval }} {{ getUnitLabel(task.unit) }}</span>
              </div>
              <div>
                <span class="text-gray-400">最后执行:</span>
                <span class="text-white ml-2">{{ formatDateTime(task.last_run_at) || '从未' }}</span>
              </div>
              <div>
                <span class="text-gray-400">下次执行:</span>
                <span class="text-white ml-2">{{ formatDateTime(task.next_run_at) || '未知' }}</span>
              </div>
              <div>
                <span class="text-gray-400">执行统计:</span>
                <span class="text-white ml-2">{{ task.success_count }}/{{ task.run_count }}</span>
              </div>
            </div>

            <div v-if="task.last_error" class="bg-red-900 bg-opacity-50 border border-red-700 rounded p-2 mb-2">
              <div class="text-red-400 text-sm">
                <strong>最后错误:</strong> {{ task.last_error }}
              </div>
            </div>

            <div class="flex justify-between text-xs text-gray-400">
              <span>创建时间: {{ formatDateTime(task.created_at) }}</span>
              <span>更新时间: {{ formatDateTime(task.updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="flex justify-center mt-6 mb-4">
        <div class="flex space-x-2">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage <= 1"
            class="px-3 py-2 bg-[#1f1f1f] hover:bg-[#272727] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            上一页
          </button>
          <span class="px-3 py-2 text-white">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="px-3 py-2 bg-[#1f1f1f] hover:bg-[#272727] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            下一页
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="tasks.length === 0 && !loading" class="text-center py-12">
        <div class="text-gray-400 mb-4">
          <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-300 mb-2">暂无定时任务</h3>
        <p class="text-gray-500 mb-4">点击上方"创建任务"按钮添加新的定时任务</p>
        <button
          @click="showCreateDialog = true"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          创建第一个任务
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
        <p class="text-gray-400">加载中...</p>
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
import { useSchedulerApi } from '../composables/useSchedulerApi'
import TaskDialog from '../components/TaskDialog.vue'
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
    // 短暂延迟后刷新状态
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

const getStatusBadgeClass = (status) => {
  const classes = {
    enabled: 'bg-green-600 text-white',
    disabled: 'bg-gray-600 text-white',
    running: 'bg-blue-600 text-white',
    error: 'bg-red-600 text-white'
  }
  return classes[status] || 'bg-gray-600 text-white'
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
/* 自定义样式 */
</style>
