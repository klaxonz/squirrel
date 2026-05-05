<template>
  <AppPageShell class="scheduled-page" variant="compact" scrollable>
    <AppToolbarFrame bordered>
      <PageHeader title="定时任务" description="管理自动化数据采集与系统同步任务">
        <template #actions>
          <div class="flex items-center gap-3">
            <Button
              variant="outline"
              @click="refreshData"
              class="h-9 px-4 text-sm font-medium"
            >
              <AppIcon name="refresh" :class="['h-4 w-4 mr-2', loading ? 'animate-spin' : '']" />
              刷新
            </Button>
            <Button
              @click="showCreateDialog = true"
              class="h-9 px-4 text-sm font-medium"
            >
              <AppIcon name="plus" class="h-4 w-4 mr-2" />
              新建任务
            </Button>
          </div>
        </template>
      </PageHeader>

      <div class="app-stat-strip">
        <div v-for="stat in statCards" :key="stat.key" class="app-stat-item">
          <span :class="['app-status-dot', stat.dotColor]"></span>
          <span>{{ stat.label }}</span>
          <span class="app-stat-value">{{ stat.value }}</span>
        </div>
      </div>
    </AppToolbarFrame>

    <div class="app-page-content">
      <div class="app-page-toolbar">
        <div class="app-tab-list shrink-0">
          <button
            v-for="opt in statusOptions"
            :key="opt.value"
            @click="setStatusFilter(opt.value)"
            class="app-tab-button"
            :class="{ 'is-active': statusFilter === opt.value }"
          >
            {{ opt.label }}
          </button>
        </div>

        <div class="relative w-72 shrink-0">
          <AppIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            v-model="searchQuery"
            @input="debouncedSearch"
            placeholder="搜索任务..."
            class="h-9 pl-9 pr-8 text-sm shadow-none w-full"
          />
          <button
            v-if="searchQuery"
            @click="clearSearch"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-muted-foreground"
          >
            <AppIcon name="close" class="h-4 w-4" />
          </button>
        </div>
      </div>

      <div class="app-surface w-full overflow-x-auto flex flex-col">
        <div class="scheduled-task-grid app-table-head gap-4 px-6 py-4 w-full">
          <div>任务详情</div>
          <div class="text-center">状态</div>
          <div>执行频率</div>
          <div>下次运行</div>
          <div class="text-right">操作</div>
        </div>

        <!-- List Content -->
        <div class="divide-y divide-border/60 w-full">
          <div v-if="loading && tasks.length === 0" class="w-full p-12 flex flex-col gap-4">
            <div v-for="i in 5" :key="i" class="h-12 w-full bg-muted/40 animate-pulse rounded-lg"></div>
          </div>

          <AppEmptyState
            v-else-if="tasks.length === 0"
            :title="hasTaskFilters ? '未找到相关任务' : '暂无定时任务'"
            :copy="hasTaskFilters ? '请尝试调整筛选条件' : '点击右上方按钮创建自动化任务'"
            class="w-full py-20"
          />

          <div
            v-for="task in tasks"
            :key="task.id"
            class="scheduled-task-grid app-table-row gap-4 px-6 py-4 items-center group w-full"
          >
            <!-- Task Info -->
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-foreground text-sm truncate">{{ task.name }}</span>
                <div v-if="task.status === 'running'" class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-50 text-[10px] font-bold text-blue-600 uppercase">
                  <span class="w-1 h-1 rounded-full bg-blue-600 animate-pulse"></span>
                  运行中
                </div>
              </div>
              <p class="text-xs text-muted-foreground line-clamp-1 mt-1">{{ task.description || '暂无描述' }}</p>
            </div>

            <!-- Status Badge -->
            <div class="flex justify-center">
              <div :class="[
                'px-2.5 py-1 rounded-md text-[11px] font-bold border',
                task.status === 'enabled' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' :
                task.status === 'disabled' ? 'bg-muted border-border text-muted-foreground' :
                task.status === 'error' ? 'bg-rose-50 border-rose-100 text-rose-700' :
                'bg-blue-50 border-blue-100 text-blue-700'
              ]">
                {{ getStatusText(task.status) }}
              </div>
            </div>

            <!-- Interval -->
            <div class="text-sm text-muted-foreground font-medium flex items-center gap-2">
              <AppIcon name="time" class="h-3.5 w-3.5 text-muted-foreground" />
              {{ task.interval }} {{ getUnitFull(task.unit) }}
            </div>

            <!-- Schedule -->
            <div class="text-xs text-muted-foreground tabular-nums">
              {{ formatDateTime(task.next_run_at) || '—' }}
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-1">
              <Button
                variant="ghost"
                size="icon"
                @click="executeTask(task)"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground hover:text-blue-600 transition-all"
                title="立即执行"
              >
                <AppIcon name="play" class="h-4 w-4 fill-current" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                @click="editTask(task)"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                title="编辑"
              >
                <AppIcon name="pencil" class="h-4 w-4" />
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <button class="h-8 w-8 flex items-center justify-center rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
                    <AppIcon name="more" class="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" class="w-40 p-1 bg-card border border-border shadow-xl rounded-lg">
                  <DropdownMenuItem v-if="task.is_active" @click="disableTask(task.id)" class="px-3 py-2 text-sm text-amber-600 rounded-md cursor-pointer hover:bg-amber-50">
                    <AppIcon name="pause" class="h-3.5 w-3.5 mr-2" />
                    暂停任务
                  </DropdownMenuItem>
                  <DropdownMenuItem v-else @click="enableTask(task.id)" class="px-3 py-2 text-sm text-blue-600 rounded-md cursor-pointer hover:bg-blue-50">
                    <AppIcon name="sync" class="h-3.5 w-3.5 mr-2" />
                    恢复任务
                  </DropdownMenuItem>
                  <DropdownMenuSeparator class="bg-muted" />
                  <DropdownMenuItem @click="confirmDeleteTask(task)" class="px-3 py-2 text-sm text-rose-600 rounded-md cursor-pointer hover:bg-rose-50">
                    <AppIcon name="trash" class="h-3.5 w-3.5 mr-2" />
                    删除任务
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="px-6 py-5 bg-muted/30 border-t border-border/50 flex items-center justify-between">
          <span class="text-xs text-muted-foreground font-medium">第 {{ currentPage }} / {{ totalPages }} 页</span>
          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              :disabled="currentPage <= 1"
              @click="goToPage(currentPage - 1)"
              class="h-8 px-3 text-xs border-border bg-card"
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              :disabled="currentPage >= totalPages"
              @click="goToPage(currentPage + 1)"
              class="h-8 px-3 text-xs border-border bg-card"
            >
              下一页
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Dialogs -->
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

    <!-- Confirmations -->
    <Dialog v-model:open="showDeleteDialog">
      <DialogContent class="max-w-[400px] p-0 overflow-hidden rounded-xl border-border">
        <div class="p-6">
          <h3 class="text-lg font-semibold text-foreground">确认删除任务</h3>
          <p class="text-sm text-muted-foreground mt-2 leading-relaxed">
            确定要删除任务 <span class="font-bold text-foreground">"{{ deletingTask?.name }}"</span> 吗？此操作将停止所有调度并清除任务记录。
          </p>
        </div>
        <div class="flex items-center justify-end gap-3 px-6 py-4 bg-muted/40 border-t border-border">
          <Button variant="ghost" @click="showDeleteDialog = false" class="h-9 px-4 text-sm font-medium">取消</Button>
          <Button @click="doDeleteTask" class="h-9 px-4 text-sm font-medium bg-rose-600 text-white hover:bg-rose-700">确认删除</Button>
        </div>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="showExecuteDialog">
      <DialogContent class="max-w-[400px] p-0 overflow-hidden rounded-xl border-border">
        <div class="p-6">
          <h3 class="text-lg font-semibold text-foreground">立即触发任务</h3>
          <p class="text-sm text-muted-foreground mt-2 leading-relaxed">
            任务 <span class="font-bold text-foreground">"{{ executingTask?.name }}"</span> 将立即进入执行队列。
          </p>
        </div>
        <div class="flex items-center justify-end gap-3 px-6 py-4 bg-muted/40 border-t border-border">
          <Button variant="ghost" @click="showExecuteDialog = false" class="h-9 px-4 text-sm font-medium">取消</Button>
          <Button @click="doExecuteTask" class="h-9 px-4 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90">开始执行</Button>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Feedback Toast -->
    <Transition name="toast">
      <div v-if="toast.visible" class="fixed bottom-6 right-6 z-50">
        <div :class="[
          'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border text-sm font-medium transition-all',
          toast.error ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-primary border-primary text-primary-foreground'
        ]">
          <AppIcon v-if="!toast.error" name="statusSuccess" class="h-4 w-4 text-emerald-400" />
          <AppIcon v-else name="warning" class="h-4 w-4 text-rose-400" />
          {{ toast.message }}
        </div>
      </div>
    </Transition>
  </AppPageShell>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import AppEmptyState from '@/components/layout/AppEmptyState.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import TaskDialog from '@/components/dialogs/TaskDialog.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog, DialogContent
} from '@/components/ui/dialog'
import { debounce } from '../utils/debounce'
import { Logger } from '@/utils/logger'
import {
  createTask as apiCreateTask,
  deleteTask as apiDeleteTask,
  disableTask as apiDisableTask,
  enableTask as apiEnableTask,
  executeTaskNow as apiExecuteTaskNow,
  getAvailableTaskClasses,
  getScheduledTasks,
  getTaskStatistics,
  updateTask as apiUpdateTask,
} from '@/api'

// Data
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
const executingTaskId = ref(null)
const deletingTaskId = ref(null)
const currentPage = ref(1)
const totalPages = ref(1)
const searchQuery = ref('')
const statusFilter = ref('all')
const showCreateDialog = ref(false)
const editingTask = ref(null)

// Dialogs
const showDeleteDialog = ref(false)
const deletingTask = ref(null)
const showExecuteDialog = ref(false)
const executingTask = ref(null)

// Toast
const toast = ref({ visible: false, message: '', error: false })
let toastTimer = null

const showToast = (message, isError = false) => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { visible: true, message, error: isError }
  toastTimer = setTimeout(() => { toast.value.visible = false }, 3000)
}

const hasTaskFilters = computed(() => {
  return Boolean(searchQuery.value || statusFilter.value !== 'all')
})

// Stats
const statCards = computed(() => [
  { key: 'total', label: '全部', value: statistics.value.total_tasks, dotColor: 'app-status-dot--muted' },
  { key: 'active', label: '活跃', value: statistics.value.active_tasks, dotColor: 'bg-blue-500' },
  { key: 'running', label: '运行', value: statistics.value.running_tasks, dotColor: 'bg-emerald-500' },
  { key: 'error', label: '异常', value: statistics.value.error_tasks, dotColor: 'bg-rose-500' },
  { key: 'today', label: '今日执行', value: statistics.value.today_executions, dotColor: 'bg-amber-500' },
])

const statusOptions = [
  { value: 'all', label: '全部' },
  { value: 'enabled', label: '就绪' },
  { value: 'disabled', label: '暂停' },
  { value: 'running', label: '运行中' },
  { value: 'error', label: '异常' }
]

// Filter setters
const setStatusFilter = (val) => {
  statusFilter.value = val
  currentPage.value = 1
  loadTasks()
}

// Load
const loadData = async () => {
  loading.value = true
  try {
    const [statsResult, classesResult] = await Promise.all([
      getTaskStatistics(),
      getAvailableTaskClasses()
    ])

    if (!statsResult.error) statistics.value = statsResult.data
    if (!classesResult.error) taskClasses.value = classesResult.data

    await loadTasks()
  } catch (error) {
    Logger.error('ScheduledTasks: Initial load failed', error)
  } finally {
    loading.value = false
  }
}

const loadTasks = async () => {
  try {
    const result = await getScheduledTasks({
      page: currentPage.value,
      page_size: 15,
      search: searchQuery.value || undefined,
      status: statusFilter.value === 'all' ? undefined : statusFilter.value
    })

    if (!result.error && result.data) {
      tasks.value = result.data.data
      totalPages.value = Math.ceil(result.data.total / 15)
    }
  } catch (error) {
    Logger.error('ScheduledTasks: Task query failed', error)
  }
}

const refreshData = async () => {
  await loadData()
}

// Task actions
const executeTask = (task) => {
  executingTask.value = task
  showExecuteDialog.value = true
}

const doExecuteTask = async () => {
  if (!executingTask.value) return
  showExecuteDialog.value = false
  executingTaskId.value = executingTask.value.id
  const result = await apiExecuteTaskNow(executingTask.value.id)
  executingTaskId.value = null
  if (!result.error) {
    showToast(`任务「${executingTask.value.name}」已开始执行`)
    setTimeout(() => refreshData(), 800)
  } else {
    showToast('执行失败', true)
  }
}

const editTask = (task) => {
  editingTask.value = task
}

const handleCreateTask = async (taskData) => {
  const result = await apiCreateTask(taskData)
  if (!result.error) {
    showCreateDialog.value = false
    showToast('任务创建成功')
    await refreshData()
  } else {
    showToast('创建失败', true)
  }
}

const handleUpdateTask = async (taskData) => {
  const result = await apiUpdateTask(editingTask.value.id, taskData)
  if (!result.error) {
    editingTask.value = null
    showToast('任务已更新')
    await refreshData()
  } else {
    showToast('更新失败', true)
  }
}

const confirmDeleteTask = (task) => {
  deletingTask.value = task
  showDeleteDialog.value = true
}

const doDeleteTask = async () => {
  if (!deletingTask.value) return
  showDeleteDialog.value = false
  deletingTaskId.value = deletingTask.value.id
  const result = await apiDeleteTask(deletingTask.value.id)
  deletingTaskId.value = null
  if (!result.error) {
    showToast(`任务已删除`)
    await refreshData()
  } else {
    showToast('删除失败', true)
  }
  deletingTask.value = null
}

const enableTask = async (id) => {
  const result = await apiEnableTask(id)
  if (!result.error) {
    showToast('任务已恢复')
    await refreshData()
  } else {
    showToast('恢复失败', true)
  }
}

const disableTask = async (id) => {
  const result = await apiDisableTask(id)
  if (!result.error) {
    showToast('任务已暂停')
    await refreshData()
  } else {
    showToast('暂停失败', true)
  }
}

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadTasks()
  }
}

// Helpers
const debouncedSearch = debounce(() => {
  currentPage.value = 1
  loadTasks()
}, 350)

const clearSearch = () => {
  searchQuery.value = ''
  debouncedSearch()
}

const resetFilters = () => {
  searchQuery.value = ''
  statusFilter.value = 'all'
  currentPage.value = 1
  loadTasks()
}

const calculateSuccessRate = (task) => {
  if (!task.run_count) return 0
  return Math.round((task.success_count / task.run_count) * 100)
}

const getUnitFull = (unit) => {
  return { seconds: '秒', minutes: '分钟', hours: '小时', days: '天' }[unit] || unit
}

const getStatusText = (status) => {
  return { enabled: '就绪', disabled: '暂停', running: '运行中', error: '异常' }[status] || status
}

const formatDateTime = (val) => {
  if (!val) return null
  const date = new Date(val)
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

onMounted(loadData)
</script>

<style scoped>
.scheduled-page {
  min-height: 100%;
  scrollbar-gutter: stable;
}

.scheduled-task-grid {
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) 120px 140px 160px 100px;
  min-width: 820px;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
