<template>
  <AppPageShell variant="compact">
    <AppTwoColumnLayout>
      <template #sidebar>
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
      </template>

      <template #header>
        <div class="min-w-0">
          <h2 class="truncate text-base font-semibold">{{ activeStatusLabel }}</h2>
          <p class="mt-0.5 text-xs text-muted-foreground">{{ taskSummary }}</p>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <div class="relative hidden w-80 md:block">
            <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="searchQuery"
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
      </template>

      <div class="shrink-0 space-y-2 border-b border-border/50 p-3 md:hidden">
        <AppSegmentedControl
          v-model="statusFilter"
          :options="statusOptions"
          aria-label="任务状态筛选"
          class="w-full"
        />
        <div class="relative">
          <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            v-model="searchQuery"
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

          <div v-else-if="tasks.length === 0" class="min-h-[20rem]">
            <AppEmptyState
              variant="plain"
              icon="time"
              :title="hasTaskFilters ? '未找到相关任务' : '暂无定时任务'"
              :copy="hasTaskFilters ? '调整筛选条件后再试。' : '创建任务后会显示在这里。'"
            />
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

      <ConfirmDialog
        v-model:open="showDeleteDialog"
        icon="trash"
        icon-bg-class="bg-destructive/10 text-destructive"
        title="删除任务？"
        cancel-label="取消"
        confirm-label="确认删除"
        confirm-variant="destructive"
        @confirm="doDeleteTask"
      >
        <template #description>
          确定要删除任务 <span class="font-semibold text-foreground">"{{ deletingTask?.name }}"</span> 吗？此操作将停止调度并清除任务记录。
        </template>
      </ConfirmDialog>

      <ConfirmDialog
        v-model:open="showExecuteDialog"
        icon="play"
        icon-bg-class="bg-primary/10 text-primary"
        icon-class="fill-current"
        title="立即触发任务？"
        cancel-label="取消"
        confirm-label="开始执行"
        @confirm="doExecuteTask"
      >
        <template #description>
          任务 <span class="font-semibold text-foreground">"{{ executingTask?.name }}"</span> 将立即进入执行队列。
        </template>
      </ConfirmDialog>
    </AppTwoColumnLayout>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import TaskDialog from '@/features/settings/components/TaskDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'
import { refDebounced } from '@vueuse/core'
import { useToast } from '@/shared/components/toast/useToast'
import { queryKeys } from '@/shared/lib/queryClient'
import type { ScheduledTask, ScheduledTaskListResponse, SchedulerStatistics } from '@/features/settings/types/scheduler'
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
} from '@/shared/api'

const queryClient = useQueryClient()
const toast = useToast()

const currentPage = ref(1)
const searchQuery = ref('')
// Debounced mirror of searchQuery — drives the tasks queryKey so typing doesn't
// fire a request per keystroke. Replaces the old hand-rolled debouncedSearch().
const searchQueryDebounced = refDebounced(searchQuery, 350)
const statusFilter = ref('all')
const showCreateDialog = ref(false)
const editingTask = ref<ScheduledTask | null>(null)
const showDeleteDialog = ref(false)
const deletingTask = ref<ScheduledTask | null>(null)
const showExecuteDialog = ref(false)
const executingTask = ref<ScheduledTask | null>(null)

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

const setStatusFilter = (val: string) => {
  statusFilter.value = val
  currentPage.value = 1
  // No manual refetch needed — tasksQuery's queryKey is reactive on
  // statusFilter/page/searchQueryDebounced, so vue-query refetches automatically.
}

// ponytail: loaders use vue-query as the single source of truth. The template
// reads derived computeds (tasks/totalPages/statistics/taskClasses) off the
// query results — no parallel mutable refs, so there's no stale-data window
// between the query cache and a local copy. Error handling is implicit: a
// failed load doesn't toast (loaders failing is routine); the list stays empty
// and the empty state renders. The tasks list refetches reactively when
// page/status/debounced-search change.
const statsQuery = useQuery({
  queryKey: queryKeys.tasks.statistics,
  queryFn: () => getTaskStatistics(),
})

const classesQuery = useQuery({
  queryKey: queryKeys.tasks.classes,
  queryFn: () => getAvailableTaskClasses(),
})

const tasksQuery = useQuery({
  queryKey: computed(() => queryKeys.tasks.list({
    page: currentPage.value,
    search: searchQueryDebounced.value || '',
    status: statusFilter.value,
  })),
  queryFn: () => getScheduledTasks({
    page: currentPage.value,
    page_size: 15,
    search: searchQueryDebounced.value || undefined,
    status: statusFilter.value === 'all' ? undefined : statusFilter.value,
  }) as Promise<ScheduledTaskListResponse>,
})

// Derived projections of the query cache — these replace the old mutable refs.
const statistics = computed<SchedulerStatistics>(() => statsQuery.data.value ?? {
  total_tasks: 0, active_tasks: 0, running_tasks: 0, error_tasks: 0, today_executions: 0,
})
const taskClasses = computed(() => classesQuery.data.value ?? {})
const tasks = computed<ScheduledTask[]>(() => tasksQuery.data.value?.data ?? [])
const totalPages = computed(() => {
  const total = tasksQuery.data.value?.total ?? 0
  return Math.max(1, Math.ceil(total / 15))
})

// Skeletons show on the first load only (isLoading); background refetches
// (isFetching) don't flash the skeleton — the prior list stays visible.
const loading = computed(() => tasksQuery.isLoading.value)

// Full reload (refresh button). refetch (not invalidate) so the button always
// forces fresh data regardless of staleTime.
const refreshData = async () => {
  await Promise.all([
    statsQuery.refetch(),
    classesQuery.refetch(),
    tasksQuery.refetch(),
  ])
}

// After a mutation, mark all task queries stale so the list/stats/classes
// re-fetch on next read. Preferred over refetch — concurrent invalidations
// dedupe and respect staleTime.
const invalidateTasks = () => {
  void queryClient.invalidateQueries({ queryKey: queryKeys.tasks.all })
}

const executeTask = (task: ScheduledTask) => {
  executingTask.value = task
  showExecuteDialog.value = true
}

let refreshTimer: ReturnType<typeof setTimeout> | null = null
onUnmounted(() => {
  if (refreshTimer) clearTimeout(refreshTimer)
})

// execute is a special case: the backend needs a beat to flip the task row to
// "running", so onSuccess only toasts + schedules a single delayed invalidation
// (no immediate refetch — that would show stale state briefly).
const executeMutation = useMutation({
  mutationFn: (task: ScheduledTask) => apiExecuteTaskNow(task.id),
  onSuccess: (_data, task) => {
    toast.success(`任务「${task.name}」已开始执行`)
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => invalidateTasks(), 800)
  },
})

const doExecuteTask = async () => {
  if (!executingTask.value) return
  showExecuteDialog.value = false
  await executeMutation.mutateAsync(executingTask.value).catch(() => { /* toast handled by MutationCache */ })
}

const editTask = (task: ScheduledTask) => {
  editingTask.value = task
}

const createMutation = useMutation({
  mutationFn: (taskData: Record<string, unknown>) => apiCreateTask(taskData),
  onSuccess: () => {
    toast.success('任务创建成功')
    showCreateDialog.value = false
    invalidateTasks()
  },
})

const handleCreateTask = async (taskData: Record<string, unknown>) => {
  await createMutation.mutateAsync(taskData).catch(() => {})
}

const updateMutation = useMutation({
  mutationFn: ({ task, taskData }: { task: ScheduledTask, taskData: Record<string, unknown> }) =>
    apiUpdateTask(task.id, taskData),
  onSuccess: () => {
    toast.success('任务已更新')
    editingTask.value = null
    invalidateTasks()
  },
})

const handleUpdateTask = async (taskData: Record<string, unknown>) => {
  if (!editingTask.value) return
  await updateMutation.mutateAsync({ task: editingTask.value, taskData }).catch(() => {})
}

const confirmDeleteTask = (task: ScheduledTask) => {
  deletingTask.value = task
  showDeleteDialog.value = true
}

const deleteMutation = useMutation({
  mutationFn: (task: ScheduledTask) => apiDeleteTask(task.id),
  onSuccess: () => {
    toast.success('任务已删除')
    invalidateTasks()
  },
})

const doDeleteTask = async () => {
  if (!deletingTask.value) return
  showDeleteDialog.value = false
  const task = deletingTask.value
  deletingTask.value = null
  await deleteMutation.mutateAsync(task).catch(() => {})
}

const enableMutation = useMutation({
  mutationFn: (id: string | number) => apiEnableTask(id),
  onSuccess: () => {
    toast.success('任务已恢复')
    invalidateTasks()
  },
})

const disableMutation = useMutation({
  mutationFn: (id: string | number) => apiDisableTask(id),
  onSuccess: () => {
    toast.success('任务已暂停')
    invalidateTasks()
  },
})

const enableTask = (id: string | number) => {
  void enableMutation.mutateAsync(id).catch(() => {})
}

const disableTask = (id: string | number) => {
  void disableMutation.mutateAsync(id).catch(() => {})
}

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    // No manual refetch — tasksQuery's queryKey is reactive on currentPage.
  }
}

// Reset to page 1 whenever the (debounced) search changes — typing or clearing
// the box both flow through here, so the list jumps to the first result page.
watch(searchQueryDebounced, () => {
  currentPage.value = 1
})

const clearSearch = () => {
  searchQuery.value = ''
  // searchQueryDebounced updates after the 350ms window → watch resets page →
  // queryKey changes → vue-query refetches. Nothing to call manually.
}

const getUnitFull = (unit: string) => {
  return ({ seconds: '秒', minutes: '分钟', hours: '小时', days: '天' } as Record<string, string>)[unit] || unit
}

const getStatusText = (status: string) => {
  return ({ enabled: '就绪', disabled: '暂停', running: '运行中', error: '异常' } as Record<string, string>)[status] || status
}

const getStatusCount = (status: string) => {
  const stats = statistics.value
  return ({
    all: stats.total_tasks,
    enabled: stats.active_tasks,
    disabled: Math.max(stats.total_tasks - stats.active_tasks, 0),
    running: stats.running_tasks,
    error: stats.error_tasks
  } as Record<string, number>)[status] || 0
}

const getStatusBadgeClass = (status: string) => {
  return ({
    enabled: 'border-border/50 bg-background text-foreground',
    disabled: 'border-border/50 bg-muted text-muted-foreground',
    running: 'border-primary/20 bg-primary/10 text-primary',
    error: 'border-destructive/20 bg-destructive/10 text-destructive'
  } as Record<string, string>)[status] || 'border-border/50 bg-muted text-muted-foreground'
}

const formatDateTime = (val: string | null | undefined) => {
  if (!val) return null
  const date = new Date(val)
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}
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

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
