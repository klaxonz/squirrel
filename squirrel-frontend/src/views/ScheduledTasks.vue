<template>
  <AppPageShell variant="compact">
    <div class="flex h-full overflow-hidden bg-background text-foreground">
      <aside class="hidden w-72 shrink-0 flex-col border-r border-border/50 bg-background lg:flex">
        <div class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4">
          <div class="min-w-0">
            <h1 class="truncate text-sm font-semibold">定时任务</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ statistics.total_tasks }} 个任务</p>
          </div>
          <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md" @click="showCreateDialog = true">
            <AppIcon name="plus" class="h-4 w-4" />
          </Button>
        </div>

        <div class="grid shrink-0 grid-cols-2 gap-2 border-b border-border/50 p-3">
          <div class="rounded-md border border-border/50 p-2">
            <div class="text-xs text-muted-foreground">活跃</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ statistics.active_tasks }}</div>
          </div>
          <div class="rounded-md border border-border/50 p-2">
            <div class="text-xs text-muted-foreground">运行</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ statistics.running_tasks }}</div>
          </div>
          <div class="rounded-md border border-border/50 p-2">
            <div class="text-xs text-muted-foreground">异常</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ statistics.error_tasks }}</div>
          </div>
          <div class="rounded-md border border-border/50 p-2">
            <div class="text-xs text-muted-foreground">今日执行</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ statistics.today_executions }}</div>
          </div>
        </div>

        <nav class="flex-1 space-y-1 overflow-y-auto p-2 custom-scrollbar">
          <button
            v-for="opt in statusOptions"
            :key="opt.value"
            @click="setStatusFilter(opt.value)"
            class="flex h-10 w-full items-center justify-between rounded-md px-2 text-left text-sm font-medium transition-colors"
            :class="statusFilter === opt.value ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
          >
            <span>{{ opt.label }}</span>
            <span class="text-xs font-normal text-muted-foreground tabular-nums">{{ getStatusCount(opt.value) }}</span>
          </button>
        </nav>
      </aside>

      <main class="flex min-w-0 flex-1 flex-col bg-background">
        <header class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4 lg:px-6">
          <div class="min-w-0">
            <h2 class="truncate text-base font-semibold">{{ activeStatusLabel }}</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ taskSummary }}</p>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <div class="relative hidden w-80 md:block">
              <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="searchQuery"
                @input="debouncedSearch"
                placeholder="搜索任务"
                class="h-9 w-full rounded-md border-border/50 pl-9 pr-8 text-sm shadow-none"
              />
              <button
                v-if="searchQuery"
                @click="clearSearch"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70 transition-colors hover:text-foreground"
              >
                <AppIcon name="close" class="h-4 w-4" />
              </button>
            </div>
            <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" @click="refreshData">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': loading }" />
            </Button>
            <Button class="h-9 rounded-md px-3 lg:hidden" @click="showCreateDialog = true">
              <AppIcon name="plus" class="h-4 w-4" />
              新建
            </Button>
          </div>
        </header>

        <div class="shrink-0 space-y-2 border-b border-border/50 p-3 md:hidden">
          <div class="flex overflow-x-auto rounded-md bg-muted p-0.5 custom-scrollbar">
            <button
              v-for="opt in statusOptions"
              :key="opt.value"
              @click="setStatusFilter(opt.value)"
              class="h-8 shrink-0 rounded-[6px] px-3 text-sm font-medium transition-colors"
              :class="statusFilter === opt.value ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
            >
              {{ opt.label }}
            </button>
          </div>
          <div class="relative">
            <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="searchQuery"
              @input="debouncedSearch"
              placeholder="搜索任务"
              class="h-9 w-full rounded-md border-border/50 pl-9 pr-8 text-sm shadow-none"
            />
            <button
              v-if="searchQuery"
              @click="clearSearch"
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70 transition-colors hover:text-foreground"
            >
              <AppIcon name="close" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <div class="mx-auto w-full max-w-[1320px] p-4 lg:p-6">
            <div class="overflow-x-auto rounded-lg border border-border/50">
              <div class="task-grid min-w-[760px] border-b border-border/50 bg-muted/20 px-4 py-3 text-xs font-medium text-muted-foreground">
                <div>任务</div>
                <div>状态</div>
                <div>频率</div>
                <div>下次运行</div>
                <div class="text-right">操作</div>
              </div>

              <div v-if="loading && tasks.length === 0" class="min-w-[760px] space-y-2 p-4">
                <div v-for="i in 5" :key="i" class="h-14 animate-pulse rounded-lg bg-accent/30" />
              </div>

              <div v-else-if="tasks.length === 0" class="flex min-h-[20rem] flex-col items-center justify-center text-center">
                <AppIcon name="time" class="h-9 w-9 text-muted-foreground/30" />
                <h2 class="mt-4 text-sm font-semibold">{{ hasTaskFilters ? '未找到相关任务' : '暂无定时任务' }}</h2>
                <p class="mt-1 text-sm text-muted-foreground">
                  {{ hasTaskFilters ? '调整筛选条件后再试。' : '创建任务后会显示在这里。' }}
                </p>
              </div>

              <div v-else class="min-w-[760px] divide-y divide-border/50">
                <div
                  v-for="task in tasks"
                  :key="task.id"
                  class="task-grid group items-center px-4 py-3 transition-colors hover:bg-accent/30"
                >
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="truncate text-sm font-semibold text-foreground">{{ task.name }}</span>
                    </div>
                    <p v-if="task.description" class="mt-1 line-clamp-1 text-xs text-muted-foreground">{{ task.description }}</p>
                  </div>

                  <div>
                    <span class="inline-flex h-7 items-center rounded-md border px-2 text-xs font-medium" :class="getStatusBadgeClass(task.status)">
                      {{ getStatusText(task.status) }}
                    </span>
                  </div>

                  <div class="flex items-center gap-2 text-sm text-muted-foreground">
                    <AppIcon name="time" class="h-3.5 w-3.5" />
                    <span>{{ task.interval }} {{ getUnitFull(task.unit) }}</span>
                  </div>

                  <div class="text-sm tabular-nums text-muted-foreground">
                    {{ formatDateTime(task.next_run_at) || '—' }}
                  </div>

                  <div class="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md text-muted-foreground" title="立即执行" @click="executeTask(task)">
                      <AppIcon name="play" class="h-4 w-4 fill-current" />
                    </Button>
                    <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md text-muted-foreground" title="编辑" @click="editTask(task)">
                      <AppIcon name="pencil" class="h-4 w-4" />
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger as-child>
                        <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md">
                          <AppIcon name="more" class="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" class="w-40">
                        <DropdownMenuItem v-if="task.is_active" @click="disableTask(task.id)">
                          <AppIcon name="pause" class="mr-2 h-4 w-4" />
                          暂停任务
                        </DropdownMenuItem>
                        <DropdownMenuItem v-else @click="enableTask(task.id)">
                          <AppIcon name="sync" class="mr-2 h-4 w-4" />
                          恢复任务
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem class="text-destructive focus:text-destructive" @click="confirmDeleteTask(task)">
                          <AppIcon name="trash" class="mr-2 h-4 w-4" />
                          删除任务
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </div>

              <div v-if="totalPages > 1" class="flex min-w-[760px] items-center justify-between border-t border-border/50 bg-muted/20 px-4 py-3">
                <span class="text-xs text-muted-foreground">第 {{ currentPage }} / {{ totalPages }} 页</span>
                <div class="flex items-center gap-2">
                  <Button variant="outline" size="sm" class="h-8 rounded-md" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">
                    上一页
                  </Button>
                  <Button variant="outline" size="sm" class="h-8 rounded-md" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">
                    下一页
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

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

      <Dialog v-model:open="showDeleteDialog">
        <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
          <DialogHeader class="border-b border-border/50 p-5 text-left">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-destructive/10 text-destructive">
              <AppIcon name="trash" class="h-5 w-5" />
            </div>
            <DialogTitle class="text-base font-semibold">删除任务？</DialogTitle>
            <DialogDescription class="text-sm leading-relaxed text-muted-foreground">
              确定要删除任务 <span class="font-semibold text-foreground">"{{ deletingTask?.name }}"</span> 吗？此操作将停止调度并清除任务记录。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter class="gap-2 bg-muted/30 p-4">
            <Button variant="outline" class="h-9 rounded-md" @click="showDeleteDialog = false">取消</Button>
            <Button variant="destructive" class="h-9 rounded-md" @click="doDeleteTask">确认删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog v-model:open="showExecuteDialog">
        <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
          <DialogHeader class="border-b border-border/50 p-5 text-left">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <AppIcon name="play" class="h-5 w-5 fill-current" />
            </div>
            <DialogTitle class="text-base font-semibold">立即触发任务？</DialogTitle>
            <DialogDescription class="text-sm leading-relaxed text-muted-foreground">
              任务 <span class="font-semibold text-foreground">"{{ executingTask?.name }}"</span> 将立即进入执行队列。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter class="gap-2 bg-muted/30 p-4">
            <Button variant="outline" class="h-9 rounded-md" @click="showExecuteDialog = false">取消</Button>
            <Button class="h-9 rounded-md" @click="doExecuteTask">开始执行</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Transition name="toast">
        <div v-if="toast.visible" class="fixed bottom-6 right-6 z-50">
          <div class="flex items-center gap-3 rounded-lg border border-border/50 bg-background px-4 py-3 text-sm font-medium text-foreground shadow-lg">
            <AppIcon v-if="!toast.error" name="statusSuccess" class="h-4 w-4 text-primary" />
            <AppIcon v-else name="warning" class="h-4 w-4 text-destructive" />
            {{ toast.message }}
          </div>
        </div>
      </Transition>
    </div>
  </AppPageShell>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
const statusFilter = ref('all')
const showCreateDialog = ref(false)
const editingTask = ref(null)
const showDeleteDialog = ref(false)
const deletingTask = ref(null)
const showExecuteDialog = ref(false)
const executingTask = ref(null)
const toast = ref({ visible: false, message: '', error: false })
let toastTimer = null

const showToast = (message, isError = false) => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { visible: true, message, error: isError }
  toastTimer = setTimeout(() => { toast.value.visible = false }, 3000)
}

const hasTaskFilters = computed(() => Boolean(searchQuery.value || statusFilter.value !== 'all'))

const taskSummary = computed(() => {
  const stats = statistics.value
  return `${stats.total_tasks} 个任务 · ${stats.active_tasks} 个活跃 · 今日执行 ${stats.today_executions}`
})

const activeStatusLabel = computed(() => {
  return statusOptions.find(option => option.value === statusFilter.value)?.label || '全部'
})

const statusOptions = [
  { value: 'all', label: '全部' },
  { value: 'enabled', label: '就绪' },
  { value: 'disabled', label: '暂停' },
  { value: 'running', label: '运行中' },
  { value: 'error', label: '异常' }
]

const setStatusFilter = (val) => {
  statusFilter.value = val
  currentPage.value = 1
  loadTasks()
}

const loadData = async () => {
  loading.value = true
  try {
    const [statsResult, classesResult] = await Promise.all([
      getTaskStatistics(),
      getAvailableTaskClasses(),
      loadTasks()
    ])

    if (!statsResult.error) statistics.value = statsResult.data
    if (!classesResult.error) taskClasses.value = classesResult.data
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

const executeTask = (task) => {
  executingTask.value = task
  showExecuteDialog.value = true
}

const doExecuteTask = async () => {
  if (!executingTask.value) return
  showExecuteDialog.value = false
  const result = await apiExecuteTaskNow(executingTask.value.id)
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
  const result = await apiDeleteTask(deletingTask.value.id)
  if (!result.error) {
    showToast('任务已删除')
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

const debouncedSearch = debounce(() => {
  currentPage.value = 1
  loadTasks()
}, 350)

const clearSearch = () => {
  searchQuery.value = ''
  debouncedSearch()
}

const getUnitFull = (unit) => {
  return { seconds: '秒', minutes: '分钟', hours: '小时', days: '天' }[unit] || unit
}

const getStatusText = (status) => {
  return { enabled: '就绪', disabled: '暂停', running: '运行中', error: '异常' }[status] || status
}

const getStatusCount = (status) => {
  const stats = statistics.value
  return {
    all: stats.total_tasks,
    enabled: stats.active_tasks,
    disabled: Math.max(stats.total_tasks - stats.active_tasks, 0),
    running: stats.running_tasks,
    error: stats.error_tasks
  }[status] || 0
}

const getStatusBadgeClass = (status) => {
  return {
    enabled: 'border-border/50 bg-background text-foreground',
    disabled: 'border-border/50 bg-muted text-muted-foreground',
    running: 'border-primary/20 bg-primary/10 text-primary',
    error: 'border-destructive/20 bg-destructive/10 text-destructive'
  }[status] || 'border-border/50 bg-muted text-muted-foreground'
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
.task-grid {
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) 7rem 8rem 10rem 7rem;
  gap: 1rem;
}

.custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }

.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
