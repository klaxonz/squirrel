<template>
  <div class="flex flex-col h-full bg-[#0f0f0f]">
    <div class="flex-none px-6 pt-6 pb-3">
      <!-- 标题和操作栏 -->
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-xl font-bold text-white">定时任务管理</h1>
        <div class="flex gap-2">
          <button
            @click="showCreateDialog = true"
            class="px-3 py-1.5 bg-[#e53935] hover:bg-[#ff5252] text-white text-xs font-medium rounded-full transition-colors"
          >
            创建任务
          </button>
          <button
            @click="refreshData"
            :disabled="loading"
            class="px-3 py-1.5 bg-[#0f0f0f] hover:bg-[#272727] disabled:opacity-50 disabled:cursor-not-allowed text-[#f1f1f1] text-xs font-medium rounded-full transition-colors border border-white/10"
          >
            刷新
          </button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-5 gap-1.5 mb-3">
        <div class="bg-[#161616] border border-white/5 rounded p-1.5 hover:bg-[#1f1f1f] transition-colors">
          <div class="text-lg font-bold text-white">{{ statistics.total_tasks }}</div>
          <div class="text-[9px] text-white/50 font-medium">总任务</div>
        </div>
        <div class="bg-[#161616] border border-white/5 rounded p-1.5 hover:bg-[#1f1f1f] transition-colors">
          <div class="text-lg font-bold text-[#4caf50]">{{ statistics.active_tasks }}</div>
          <div class="text-[9px] text-white/50 font-medium">活跃</div>
        </div>
        <div class="bg-[#161616] border border-white/5 rounded p-1.5 hover:bg-[#1f1f1f] transition-colors">
          <div class="text-lg font-bold text-[#2196f3]">{{ statistics.running_tasks }}</div>
          <div class="text-[9px] text-white/50 font-medium">运行中</div>
        </div>
        <div class="bg-[#161616] border border-white/5 rounded p-1.5 hover:bg-[#1f1f1f] transition-colors">
          <div class="text-lg font-bold text-[#e53935]">{{ statistics.error_tasks }}</div>
          <div class="text-[9px] text-white/50 font-medium">错误</div>
        </div>
        <div class="bg-[#161616] border border-white/5 rounded p-1.5 hover:bg-[#1f1f1f] transition-colors">
          <div class="text-lg font-bold text-[#ff9800]">{{ statistics.today_executions }}</div>
          <div class="text-[9px] text-white/50 font-medium">今日执行</div>
        </div>
      </div>

      <!-- 调度器状态和筛选 -->
      <div class="flex items-center gap-2 mb-3">
        <!-- 调度器状态 -->
        <div class="flex items-center gap-2 bg-[#161616] border border-white/5 rounded px-2.5 py-1.5">
          <div
            class="w-1.5 h-1.5 rounded-full"
            :class="schedulerStatus?.running ? 'bg-[#4caf50] shadow-lg shadow-[#4caf50]/50' : 'bg-[#e53935] shadow-lg shadow-[#e53935]/50'"
          ></div>
          <span class="text-[10px] font-medium text-white">
            <span :class="schedulerStatus?.running ? 'text-[#4caf50]' : 'text-[#e53935]'">{{ schedulerStatus?.running ? '运行中' : '已停止' }}</span>
          </span>
          <button
            v-if="!schedulerStatus?.running"
            @click="enableScheduler"
            :disabled="loading"
            class="ml-1 px-2 py-0.5 bg-[#4caf50] hover:bg-[#66bb6a] disabled:opacity-50 disabled:cursor-not-allowed text-white text-[10px] font-medium rounded-full transition-colors"
          >
            启用
          </button>
          <button
            v-if="schedulerStatus?.running"
            @click="disableScheduler"
            :disabled="loading"
            class="ml-1 px-2 py-0.5 bg-[#e53935] hover:bg-[#ff5252] disabled:opacity-50 disabled:cursor-not-allowed text-white text-[10px] font-medium rounded-full transition-colors"
          >
            禁用
          </button>
        </div>
        <!-- 搜索和过滤 -->
        <input
          v-model="searchQuery"
          @input="debouncedSearch"
          type="text"
          placeholder="搜索任务..."
          class="flex-1 min-w-[150px] px-3 py-1.5 bg-[#161616] border border-white/10 rounded text-white text-[10px] placeholder-white/30 focus:outline-none focus:border-[#e53935] focus:ring-1 focus:ring-[#e53935] transition-colors"
        >
        <select
          v-model="statusFilter"
          @change="loadTasks"
          class="px-3 py-1.5 bg-[#161616] border border-white/10 rounded text-white text-[10px] focus:outline-none focus:border-[#e53935] focus:ring-1 focus:ring-[#e53935] transition-colors"
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
          class="px-3 py-1.5 bg-[#161616] border border-white/10 rounded text-white text-[10px] focus:outline-none focus:border-[#e53935] focus:ring-1 focus:ring-[#e53935] transition-colors"
        >
          <option value="">所有类型</option>
          <option value="system">系统任务</option>
          <option value="user">用户任务</option>
          <option value="plugin">插件任务</option>
        </select>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
      <!-- 表格 -->
      <div class="bg-[#1f1f1f] border border-white/5 rounded-lg overflow-hidden">
        <table class="w-full">
          <thead class="bg-[#161616] border-b border-white/5">
            <tr>
              <th class="px-3 py-2 text-left text-[10px] font-semibold text-white/70 uppercase tracking-wider">任务名称</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold text-white/70 uppercase tracking-wider">状态</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold text-white/70 uppercase tracking-wider">类型</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold text-white/70 uppercase tracking-wider">执行间隔</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold text-white/70 uppercase tracking-wider">最后执行</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold text-white/70 uppercase tracking-wider">下次执行</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold text-white/70 uppercase tracking-wider">成功/总数</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold text-white/70 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
            <tr
              v-for="task in tasks"
              :key="task.id"
              class="hover:bg-[#272727] transition-colors"
            >
              <!-- 任务名称 -->
              <td class="px-3 py-2">
                <div class="text-xs font-medium text-white">{{ task.name }}</div>
                <div v-if="task.description" class="text-[10px] text-white/50 mt-0.5">{{ task.description }}</div>
                <div v-if="task.last_error" class="text-[10px] text-[#e53935] mt-0.5" :title="task.last_error">错误: {{ task.last_error }}</div>
              </td>

              <!-- 状态 -->
              <td class="px-3 py-2">
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap"
                  :class="getStatusBadgeClass(task.status)"
                >
                  {{ getStatusText(task.status) }}
                </span>
              </td>

              <!-- 类型 -->
              <td class="px-3 py-2">
                <span class="text-[10px] text-white/70">{{ getTypeText(task.task_type) }}</span>
              </td>

              <!-- 执行间隔 -->
              <td class="px-3 py-2">
                <span class="text-[10px] text-white">{{ task.interval }} {{ getUnitLabel(task.unit) }}</span>
              </td>

              <!-- 最后执行 -->
              <td class="px-3 py-2">
                <span class="text-[10px] text-white/70">{{ formatDateTime(task.last_run_at) || '从未' }}</span>
              </td>

              <!-- 下次执行 -->
              <td class="px-3 py-2">
                <span class="text-[10px] text-white/70">{{ formatDateTime(task.next_run_at) || '未知' }}</span>
              </td>

              <!-- 成功/总数 -->
              <td class="px-3 py-2 text-center">
                <span class="text-[10px] text-white">{{ task.success_count }}/{{ task.run_count }}</span>
              </td>

              <!-- 操作 -->
              <td class="px-3 py-2">
                <div class="flex gap-1 justify-end">
                  <button
                    v-if="!task.is_legacy"
                    @click="executeTaskNow(task.id)"
                    :disabled="loading"
                    class="px-2 py-0.5 bg-[#2196f3] hover:bg-[#42a5f5] disabled:opacity-50 disabled:cursor-not-allowed text-white text-[10px] font-medium rounded-full transition-colors"
                    title="立即执行"
                  >
                    执行
                  </button>
                  <button
                    v-if="!task.is_legacy"
                    @click="editTask(task)"
                    class="px-2 py-0.5 bg-[#ff9800] hover:bg-[#ffa726] text-white text-[10px] font-medium rounded-full transition-colors"
                    title="编辑"
                  >
                    编辑
                  </button>
                  <button
                    v-if="!task.is_legacy && task.is_active"
                    @click="disableTask(task.id)"
                    class="px-2 py-0.5 bg-white/10 hover:bg-white/20 text-white text-[10px] font-medium rounded-full transition-colors"
                    title="禁用"
                  >
                    禁用
                  </button>
                  <button
                    v-if="!task.is_legacy && !task.is_active"
                    @click="enableTask(task.id)"
                    class="px-2 py-0.5 bg-[#4caf50] hover:bg-[#66bb6a] text-white text-[10px] font-medium rounded-full transition-colors"
                    title="启用"
                  >
                    启用
                  </button>
                   <button
                     v-if="!task.is_legacy && task.task_type !== 'system'"
                     @click="deleteTask(task.id)"
                     class="px-2 py-0.5 bg-[#e53935] hover:bg-[#ff5252] text-white text-[10px] font-medium rounded-full transition-colors"
                     title="删除"
                   >
                     删除
                   </button>
                  <span
                    v-if="task.is_legacy"
                    class="px-2 py-0.5 bg-white/10 text-white/50 text-[10px] font-medium rounded-full"
                    title="系统内置任务，不可修改"
                  >
                    系统
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="flex justify-center mt-6 mb-4">
        <div class="flex items-center gap-2">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage <= 1"
            class="px-4 py-2 bg-[#161616] border border-white/10 hover:bg-[#1f1f1f] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            上一页
          </button>
          <div class="px-4 py-2 bg-[#161616] border border-white/10 text-white text-sm font-medium rounded-lg">
            第 {{ currentPage }} / {{ totalPages }} 页
          </div>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="px-4 py-2 bg-[#161616] border border-white/10 hover:bg-[#1f1f1f] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            下一页
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="tasks.length === 0 && !loading" class="text-center py-16">
        <div class="bg-[#161616] border border-white/5 rounded-lg p-8 max-w-md mx-auto">
          <svg class="w-20 h-20 mx-auto mb-4 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <h3 class="text-lg font-semibold text-white mb-2">暂无定时任务</h3>
          <p class="text-sm text-white/50 mb-6">点击下方按钮创建您的第一个定时任务</p>
          <button
            @click="showCreateDialog = true"
            class="px-5 py-2.5 bg-[#e53935] hover:bg-[#ff5252] text-white text-sm font-medium rounded-full transition-colors"
          >
            创建第一个任务
          </button>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-16">
        <div class="inline-flex items-center gap-3 bg-[#161616] border border-white/5 rounded-lg px-6 py-4">
          <div class="animate-spin rounded-full h-5 w-5 border-2 border-white/20 border-t-[#e53935]"></div>
          <span class="text-sm text-white/70 font-medium">加载中...</span>
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
    enabled: 'bg-[#4caf50] text-white',
    disabled: 'bg-white/10 text-white/50',
    running: 'bg-[#2196f3] text-white',
    error: 'bg-[#e53935] text-white'
  }
  return classes[status] || 'bg-white/10 text-white/50'
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
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
