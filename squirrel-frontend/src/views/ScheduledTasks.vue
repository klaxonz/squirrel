<template>
  <AppPageShell class="scheduled-page">
    <AppToolbarFrame class="toolbar-container">
      <!-- Stats Row -->
      <div class="flex items-center gap-3 mt-4 overflow-x-auto">
        <div
          v-for="stat in signals"
          :key="stat.key"
          class="flex items-center gap-2 px-3 py-2 rounded-lg border border-border/20 bg-muted/10 shrink-0"
        >
          <component :is="stat.icon" :class="['h-4 w-4 shrink-0', stat.color]" />
          <div class="flex flex-col min-w-0">
            <span class="text-[10px] text-muted-foreground leading-none">{{ stat.label }}</span>
            <span class="text-sm font-semibold tabular-nums text-foreground leading-tight mt-0.5">{{ stat.value }}</span>
          </div>
        </div>
      </div>
    </AppToolbarFrame>

    <!-- Main Content -->
    <div class="content-container flex-1 flex flex-col min-h-0 overflow-hidden">

      <!-- Search & Filter Bar -->
      <div class="px-4 py-3 border-b border-border/30">
        <div class="flex items-center gap-3 flex-wrap">
          <!-- Search with border -->
          <div class="relative flex-1 min-w-[180px] border border-border/60 rounded-lg bg-background">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
            <Input
              v-model="searchQuery"
              @input="debouncedSearch"
              placeholder="搜索任务名称、描述或异常..."
              class="pl-8 pr-8 bg-transparent border-none h-8 text-[11px] focus-visible:ring-0 placeholder:text-muted-foreground/30 shadow-none"
            />
            <button
              v-if="searchQuery"
              @click="clearSearch"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-foreground transition-colors"
            >
              <X class="h-3 w-3" />
            </button>
          </div>

          <div class="flex items-center gap-1.5 shrink-0">
            <Button
              variant="outline"
              size="sm"
              class="h-8 px-3 text-[11px] font-medium border-border/40 text-muted-foreground hover:text-foreground hover:border-border/80 transition-all shadow-none"
              :disabled="loading"
              @click="refreshData"
            >
              <RefreshCw :class="['h-3.5 w-3.5 mr-1.5', loading ? 'animate-spin' : '']" />
              刷新
            </Button>

            <Button
              size="sm"
              class="h-8 px-4 text-[11px] font-medium transition-all shadow-none"
              @click="showCreateDialog = true"
            >
              <Plus class="h-3.5 w-3.5 mr-1.5" />
              新建任务
            </Button>
          </div>

          <div class="h-5 w-px bg-border/20 shrink-0"></div>

          <div class="scheduled-filter-scroll shrink-0">
            <AppSegmentedControl
              v-model="statusFilter"
              variant="dense"
              class="scheduled-filter-tabs"
              :options="statusOptions"
              aria-label="任务状态筛选"
              @change="setStatusFilter"
            />
          </div>

          <div class="h-5 w-px bg-border/20 shrink-0 hidden md:block"></div>

          <div class="scheduled-filter-scroll shrink-0">
            <AppSegmentedControl
              v-model="typeFilter"
              variant="dense"
              class="scheduled-filter-tabs scheduled-filter-tabs--compact"
              :options="typeOptions"
              aria-label="任务类型筛选"
              @change="setTypeFilter"
            />
          </div>
        </div>
      </div>

      <!-- Table Area -->
      <div class="flex-1 overflow-hidden flex flex-col min-h-0">

        <!-- Empty State -->
        <AppEmptyState
          v-if="!loading && tasks.length === 0"
          class="scheduled-empty-state"
          variant="dense"
          eyebrow="调度中心"
          :title="hasTaskFilters ? '没有匹配的任务' : '当前没有任务'"
          :copy="hasTaskFilters ? '调整搜索或筛选条件后再试。' : '点击上方按钮部署第一个任务。'"
        >
          <template #actions>
            <Button v-if="hasTaskFilters" size="sm" variant="secondary" @click="resetFilters">清空筛选</Button>
            <Button size="sm" @click="showCreateDialog = true">
              <Plus class="h-3.5 w-3.5 mr-1.5" />
              新建任务
            </Button>
          </template>
        </AppEmptyState>

        <!-- Table -->
        <div v-else class="flex-1 overflow-auto min-h-0">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="sticky top-0 z-10 bg-background border-b border-border/30">
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-left">任务</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-center w-20">状态</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-center w-20">频率</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-left w-36">上次执行</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-left w-36">下次计划</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-center w-16">执行数</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-center w-16">成功率</th>
                <th class="px-4 py-3 text-[11px] font-medium text-muted-foreground text-right w-12"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/10">
              <!-- Loading Skeleton -->
              <template v-if="loading && tasks.length === 0">
                <tr v-for="i in 6" :key="i" class="animate-pulse">
                  <td class="px-4 py-4"><div class="h-3 w-32 bg-muted/30 rounded"></div></td>
                  <td class="px-4 py-4"><div class="h-3 w-12 bg-muted/20 rounded mx-auto"></div></td>
                  <td class="px-4 py-4"><div class="h-3 w-10 bg-muted/20 rounded mx-auto"></div></td>
                  <td class="px-4 py-4"><div class="h-3 w-20 bg-muted/20 rounded"></div></td>
                  <td class="px-4 py-4"><div class="h-3 w-20 bg-muted/20 rounded"></div></td>
                  <td class="px-4 py-4"><div class="h-3 w-10 bg-muted/20 rounded mx-auto"></div></td>
                  <td class="px-4 py-4"><div class="h-3 w-10 bg-muted/20 rounded mx-auto"></div></td>
                  <td class="px-4 py-4"><div class="h-5 w-5 bg-muted/20 rounded ml-auto"></div></td>
                </tr>
              </template>

              <!-- Data Rows -->
              <tr
                v-for="task in tasks"
                :key="task.id"
                class="hover:bg-muted/30 transition-all"
              >
                <!-- Task Info -->
                <td class="px-4 py-4 align-middle">
                  <div class="flex flex-col gap-0.5">
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-foreground text-[12px]">{{ task.name }}</span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground">{{ getTypeText(task.task_type) }}</span>
                    </div>
                    <p class="text-[11px] text-muted-foreground line-clamp-1">{{ task.description || '无描述' }}</p>
                    <div v-if="task.last_error" class="flex items-center gap-1 text-[10px] text-destructive" :title="task.last_error">
                      <AlertCircle class="h-3 w-3 shrink-0" />
                      <span class="truncate">{{ task.last_error }}</span>
                    </div>
                  </div>
                </td>

                <!-- Status -->
                <td class="px-4 py-4 align-middle text-center">
                  <span class="text-[11px] text-foreground">{{ getStatusText(task.status) }}</span>
                </td>

                <!-- Frequency -->
                <td class="px-4 py-4 align-middle text-center">
                  <span class="text-[12px] font-medium text-foreground tabular-nums">{{ task.interval }}{{ getUnitShort(task.unit) }}</span>
                </td>

                <!-- Last Run -->
                <td class="px-4 py-4 align-middle">
                  <span class="text-[11px] text-muted-foreground tabular-nums">{{ formatDateTime(task.last_run_at) || '—' }}</span>
                </td>

                <!-- Next Run -->
                <td class="px-4 py-4 align-middle">
                  <span class="text-[11px] text-foreground tabular-nums">{{ formatDateTime(task.next_run_at) || '—' }}</span>
                </td>

                <!-- Run Count -->
                <td class="px-4 py-4 align-middle text-center">
                  <span class="text-[11px] text-muted-foreground tabular-nums">{{ task.run_count || 0 }}</span>
                </td>

                <!-- Success Rate -->
                <td class="px-4 py-4 align-middle text-center">
                  <span class="text-[11px] font-medium text-foreground tabular-nums">{{ calculateSuccessRate(task) }}%</span>
                </td>

                <!-- Actions -->
                <td class="px-4 py-4 align-middle text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger as-child>
                      <Button variant="ghost" size="sm" class="h-8 w-8 p-0 text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0">
                        <MoreVertical class="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" class="w-40 bg-background border border-border/40">
                      <DropdownMenuItem @click="executeTask(task)" :disabled="executingTaskId === task.id" class="gap-2 px-3 py-2 cursor-pointer">
                        <Play class="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                        <span class="text-[11px]">{{ executingTaskId === task.id ? '触发中...' : '立即触发' }}</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem @click="editTask(task)" class="gap-2 px-3 py-2 cursor-pointer">
                        <Pencil class="h-3.5 w-3.5 shrink-0" />
                        <span class="text-[11px]">编辑配置</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem v-if="task.is_active" @click="disableTask(task.id)" class="gap-2 px-3 py-2 cursor-pointer">
                        <Pause class="h-3.5 w-3.5 text-amber-500 shrink-0" />
                        <span class="text-[11px]">暂停调度</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem v-else @click="enableTask(task.id)" class="gap-2 px-3 py-2 cursor-pointer">
                        <Zap class="h-3.5 w-3.5 text-primary shrink-0" />
                        <span class="text-[11px]">恢复调度</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        @click="confirmDeleteTask(task)"
                        :disabled="task.task_type === 'system' || deletingTaskId === task.id"
                        class="gap-2 px-3 py-2 cursor-pointer text-destructive"
                      >
                        <Loader2 v-if="deletingTaskId === task.id" class="h-3.5 w-3.5 animate-spin shrink-0" />
                        <Trash2 v-else class="h-3.5 w-3.5 shrink-0" />
                        <span class="text-[11px]">{{ deletingTaskId === task.id ? '删除中...' : '移除任务' }}</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 0" class="flex items-center justify-between px-4 py-3 border-t border-border/20">
          <p class="text-[11px] text-muted-foreground">
            共 {{ statistics.total_tasks }} 个任务
          </p>
          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              class="h-8 px-3 text-[11px]"
              :disabled="currentPage <= 1 || loading"
              @click="goToPage(currentPage - 1)"
            >
              上一页
            </Button>
            <span class="text-[11px] text-muted-foreground px-2">
              {{ currentPage }} / {{ totalPages }}
            </span>
            <Button
              variant="outline"
              size="sm"
              class="h-8 px-3 text-[11px]"
              :disabled="currentPage >= totalPages || loading"
              @click="goToPage(currentPage + 1)"
            >
              下一页
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
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

    <!-- Delete Confirm Dialog -->
    <Dialog v-model:open="showDeleteDialog">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle class="text-base font-bold">确认移除任务</DialogTitle>
          <DialogDescription class="text-[11px] text-muted-foreground/50">
            确定要移除任务 <strong class="text-foreground/60">"{{ deletingTask?.name }}"</strong> 吗？此操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button
            variant="ghost"
            size="sm"
            class="h-8 px-4 text-[10px] font-bold uppercase tracking-wider"
            @click="showDeleteDialog = false"
          >
            取消
          </Button>
          <Button
            size="sm"
            class="h-8 px-4 text-[10px] font-bold uppercase tracking-wider bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/20"
            @click="doDeleteTask"
          >
            确认移除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Execute Confirm Dialog -->
    <Dialog v-model:open="showExecuteDialog">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle class="text-base font-bold">确认立即触发</DialogTitle>
          <DialogDescription class="text-[11px] text-muted-foreground/50">
            任务 <strong class="text-foreground/60">"{{ executingTask?.name }}"</strong> 将跳过调度周期立即执行，是否继续？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button
            variant="ghost"
            size="sm"
            class="h-8 px-4 text-[10px] font-bold uppercase tracking-wider"
            @click="showExecuteDialog = false"
          >
            取消
          </Button>
          <Button
            size="sm"
            class="h-8 px-4 text-[11px] font-medium"
            @click="doExecuteTask"
          >
            立即执行
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Feedback Toast -->
    <Transition name="toast">
      <div v-if="toast.visible" :class="['save-toast', toast.error ? 'save-toast--error' : 'save-toast--success']">
        <CheckCircle2 v-if="!toast.error" class="h-4 w-4 shrink-0" />
        <AlertCircle v-else class="h-4 w-4 shrink-0" />
        <span class="text-xs font-semibold">{{ toast.message }}</span>
      </div>
    </Transition>
  </AppPageShell>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import {
  Activity, RefreshCw, Plus, Search, Zap, AlertCircle,
  CheckCircle2, Play, Pause, Pencil, Trash2, MoreVertical,
  Loader2, X
} from 'lucide-vue-next'
import AppEmptyState from '@/components/layout/AppEmptyState.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import AppSegmentedControl from '@/components/layout/AppSegmentedControl.vue'
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue'
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
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter
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
const typeFilter = ref('all')
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
  toastTimer = setTimeout(() => { toast.value.visible = false }, 2800)
}

const hasTaskFilters = computed(() => {
  return Boolean(searchQuery.value || statusFilter.value !== 'all' || typeFilter.value !== 'all')
})

// Stats
const signals = computed(() => [
  {
    key: 'total',
    label: '任务总数',
    value: statistics.value.total_tasks,
    icon: Activity,
    color: 'text-muted-foreground'
  },
  {
    key: 'active',
    label: '活跃',
    value: statistics.value.active_tasks,
    icon: Zap,
    color: 'text-foreground'
  },
  {
    key: 'running',
    label: '运行中',
    value: statistics.value.running_tasks,
    icon: Loader2,
    color: 'text-muted-foreground'
  },
  {
    key: 'error',
    label: '异常',
    value: statistics.value.error_tasks,
    icon: AlertCircle,
    color: 'text-destructive'
  },
  {
    key: 'today',
    label: '今日完成',
    value: statistics.value.today_executions,
    icon: CheckCircle2,
    color: 'text-foreground'
  },
])

const statusOptions = [
  { value: 'all', label: '全部' },
  { value: 'enabled', label: '就绪' },
  { value: 'disabled', label: '暂停' },
  { value: 'running', label: '运行' },
  { value: 'error', label: '异常' }
]

const typeOptions = [
  { value: 'all', label: '全部' },
  { value: 'system', label: '核心' },
  { value: 'user', label: '用户' },
  { value: 'plugin', label: '插件' }
]

// Pagination: visible page buttons
const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages = []
  if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  } else if (current >= total - 3) {
    pages.push(1)
    pages.push('...')
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    pages.push('...')
    for (let i = current - 1; i <= current + 1; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  }
  return pages
})

// Filter setters
const setStatusFilter = (val) => {
  statusFilter.value = val
  currentPage.value = 1
  loadTasks()
}

const setTypeFilter = (val) => {
  typeFilter.value = val
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
      status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      task_type: typeFilter.value === 'all' ? undefined : typeFilter.value
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
    showToast(`任务「${executingTask.value.name}」已触发`)
    setTimeout(() => refreshData(), 600)
  } else {
    showToast('触发失败', true)
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
    showToast('创建失败：' + (result.message || '未知错误'), true)
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
  if (task.task_type === 'system') return
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
    showToast(`任务「${deletingTask.value.name}」已移除`)
    await refreshData()
  } else {
    showToast('删除失败', true)
  }
  deletingTask.value = null
}

const enableTask = async (id) => {
  const result = await apiEnableTask(id)
  if (!result.error) {
    showToast('任务已恢复调度')
    await refreshData()
  } else {
    showToast('操作失败', true)
  }
}

const disableTask = async (id) => {
  const result = await apiDisableTask(id)
  if (!result.error) {
    showToast('任务已暂停调度')
    await refreshData()
  } else {
    showToast('操作失败', true)
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
  typeFilter.value = 'all'
  currentPage.value = 1
  loadTasks()
}

const calculateSuccessRate = (task) => {
  if (!task.run_count) return 0
  return Math.round((task.success_count / task.run_count) * 100)
}

const getUnitShort = (unit) => {
  return { seconds: 's', minutes: 'm', hours: 'h', days: 'd' }[unit] || unit
}

const getStatusText = (status) => {
  return { enabled: '就绪', disabled: '暂停', running: '运行中', error: '异常' }[status] || status
}

const getTypeText = (type) => {
  return { system: '核心', user: '用户', plugin: '插件' }[type] || type
}

const formatDateTime = (val) => {
  if (!val) return null
  const date = new Date(val)
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

onMounted(loadData)
</script>

<style scoped>
/* Container: consistent with other pages */
.content-container {
  max-width: 100%;
  padding-left: var(--app-page-gutter);
  padding-right: var(--app-page-gutter);
  width: 100%;
}

@media (min-width: 640px) {
  .content-container {
    padding-left: var(--app-page-gutter-sm);
    padding-right: var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .content-container {
    padding-left: var(--app-page-gutter-lg);
    padding-right: var(--app-page-gutter-lg);
  }
}

.scheduled-filter-scroll {
  overflow-x: auto;
}

.scheduled-filter-tabs {
  min-width: max-content;
}

.scheduled-filter-tabs--compact :deep(.app-segmented-control__item) {
  padding-inline: 0.55rem;
}

.scheduled-empty-state {
  min-height: 22rem;
  margin: 1rem 0;
}

/* Typography */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}

/* Toast */
.save-toast {
  position: fixed;
  bottom: 1.75rem;
  right: 1.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  box-shadow: 0 8px 32px hsl(var(--foreground) / 0.15);
  z-index: 200;
}
.save-toast--error {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}
.save-toast--success {
  background: hsl(var(--foreground));
  color: hsl(var(--background));
}
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(0.75rem) scale(0.95);
}
</style>
