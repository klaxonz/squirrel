<template>
  <AppPageShell variant="compact" fill>
    <AppTwoColumnLayout content-width="87.5rem">
      <template #sidebar>
        <AppSidebarHeader title="定时任务" :subtitle="`${statistics.total_tasks} 个任务`">
          <template #actions>
            <Button variant="ghost" size="icon-sm" @click="showCreateDialog = true">
              <AppIcon name="plus" class="h-4 w-4" />
            </Button>
          </template>
        </AppSidebarHeader>

        <div class="grid shrink-0 grid-cols-2 gap-2 app-divider-bottom p-3">
          <AppStatCard label="活跃" :value="statistics.active_tasks" />
          <AppStatCard label="运行" :value="statistics.running_tasks" />
          <AppStatCard label="异常" :value="statistics.error_tasks" />
          <AppStatCard label="今日执行" :value="statistics.today_executions" />
        </div>

        <nav class="app-workbench__nav custom-scrollbar" aria-label="任务状态">
          <AppListOption
            v-for="opt in statusOptions"
            :key="opt.value"
            compact
            :selected="statusFilter === opt.value"
            @click="setStatusFilter(opt.value)"
          >
            <span class="min-w-0 flex-1 truncate">{{ opt.label }}</span>
            <span class="text-xs font-normal text-muted-foreground tabular-nums">{{ getStatusCount(opt.value) }}</span>
          </AppListOption>
        </nav>
      </template>

      <template #header>
        <AppPaneHeader :title="activeStatusLabel" :subtitle="taskSummary">
          <template #actions>
            <AppSearchInput v-model="searchQuery" placeholder="搜索任务" class="hidden w-80 md:block" />
            <Button variant="ghost" size="icon-sm" @click="refreshData">
              <AppSpinner v-if="loading" size="sm" />
              <AppIcon v-else name="refresh" class="h-4 w-4" />
            </Button>
          </template>
        </AppPaneHeader>
      </template>

      <div class="shrink-0 space-y-2 app-divider-bottom p-3 md:hidden">
        <AppSegmentedControl
          v-model="statusFilter"
          :options="statusOptions"
          aria-label="任务状态筛选"
          class="w-full"
        />
        <AppSearchInput v-model="searchQuery" placeholder="搜索任务" />
      </div>

      <div class="app-workbench__content app-table-content scheduled-tasks-content">
        <div class="app-table-shell">
          <div class="app-table-frame">
          <div class="app-table-head task-grid">
            <div>任务</div>
            <div>状态</div>
            <div>频率</div>
            <div>下次运行</div>
            <div class="text-right">操作</div>
          </div>

          <div v-if="loading && tasks.length === 0" class="app-table-loading app-content-stack app-content-stack--dense">
            <AppSkeleton v-for="i in 5" :key="i" height="3.5rem" rounded="var(--radius-lg)" shimmer />
          </div>

          <div v-else-if="tasks.length === 0" class="app-page-empty app-page-empty--compact">
            <AppEmptyState
              variant="plain"
              icon="time"
              :title="hasTaskFilters ? '未找到相关任务' : '暂无定时任务'"
              :copy="hasTaskFilters ? '调整筛选条件后再试。' : '创建任务后会显示在这里。'"
            />
          </div>

              <div v-else class="app-table-body">
                <div
                  v-for="task in tasks"
                  :key="task.id"
                  class="app-table-row task-grid group"
                >
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="truncate text-sm font-semibold text-foreground">{{ task.name }}</span>
                    </div>
                    <p v-if="task.description" class="mt-1 line-clamp-1 text-xs text-muted-foreground">{{ task.description }}</p>
                  </div>

                  <div>
                    <Badge :variant="getStatusBadgeVariant(task.status)" class="h-7 px-2.5">
                      {{ getStatusText(task.status) }}
                    </Badge>
                  </div>

                  <div class="flex items-center gap-2 text-sm text-muted-foreground">
                    <AppIcon name="time" class="h-3.5 w-3.5" />
                    <span>{{ task.interval }} {{ getUnitFull(task.unit) }}</span>
                  </div>

                  <div class="text-sm tabular-nums text-muted-foreground">
                    {{ formatDateTime(task.next_run_at) || '—' }}
                  </div>

                  <div class="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="icon-sm" class="text-muted-foreground" title="立即执行" @click="executeTask(task)">
                      <AppIcon name="play" class="h-4 w-4 fill-current" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" class="text-muted-foreground" title="编辑" @click="editTask(task)">
                      <AppIcon name="pencil" class="h-4 w-4" />
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger as-child>
                        <Button variant="ghost" size="icon-sm">
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

              <div v-if="totalPages > 1" class="app-table-pager">
                <span class="text-xs text-muted-foreground">第 {{ currentPage }} / {{ totalPages }} 页</span>
                <div class="flex items-center gap-2">
                  <Button variant="outline" size="sm" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">
                    上一页
                  </Button>
                  <Button variant="outline" size="sm" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">
                    下一页
                  </Button>
                </div>
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
import { computed, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import AppPaneHeader from '@/shared/components/layout/AppPaneHeader.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppSidebarHeader from '@/shared/components/layout/AppSidebarHeader.vue'
import AppStatCard from '@/shared/components/layout/AppStatCard.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import TaskDialog from '@/features/settings/components/TaskDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import { Button } from '@/shared/ui/button'
import { Badge } from '@/shared/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'
import type { ScheduledTask } from '@/features/settings/types/scheduler'
import {
  getUnitFull,
  getStatusText,
  getStatusCount as getStatusCountFor,
  getStatusBadgeVariant,
  formatDateTime,
} from '@/features/settings/lib/scheduledTaskPresenters'
import { useScheduledTaskQueries } from '@/features/settings/composables/useScheduledTaskQueries'
import { useScheduledTaskMutations } from '@/features/settings/composables/useScheduledTaskMutations'


const currentPage = ref(1)
const searchQuery = ref('')
const searchQueryDebounced = ref('')
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, (nextValue) => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    searchQueryDebounced.value = nextValue
  }, 350)
})
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

// ponytail: the three vue-query loaders + derived projections + the
// invalidate/refresh entry points live in useScheduledTaskQueries. The list
// queryKey is reactive on page/search/status so vue-query refetches on its own
// — no manual refetch, no stale-data window between cache and a local copy.
const {
  statistics,
  taskClasses,
  tasks,
  totalPages,
  loading,
  refreshData,
  invalidateTasks,
} = useScheduledTaskQueries({
  page: currentPage,
  search: searchQueryDebounced,
  status: statusFilter,
})

let refreshTimer: ReturnType<typeof setTimeout> | null = null
onUnmounted(() => {
  if (refreshTimer) clearTimeout(refreshTimer)
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
})

// ponytail: the six task mutations + their toast/invalidate contract live in
// useScheduledTaskMutations. Dialog-state toggles are injected callbacks
// (onCreated/onUpdated) so the composable doesn't own dialog visibility; the
// delayed-invalidation timer for execute is also injected so the host owns it.
const {
  handleCreateTask: doCreateTask,
  handleUpdateTask: doUpdateTask,
  doDeleteTask: doDelete,
  enableTask,
  disableTask,
  executeTask: doExecute,
} = useScheduledTaskMutations({
  invalidateTasks,
  scheduleInvalidate: (delayMs) => {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => invalidateTasks(), delayMs)
  },
  onCreated: () => { showCreateDialog.value = false },
  onUpdated: () => { editingTask.value = null },
})

// Dialog flows: the row action opens the relevant confirm dialog (stashing the
// target task); the dialog's @confirm resolves the stashed task and fires the
// mutation. Save flows pass taskData straight through.
const executeTask = (task: ScheduledTask) => {
  executingTask.value = task
  showExecuteDialog.value = true
}
const doExecuteTask = async () => {
  if (!executingTask.value) return
  showExecuteDialog.value = false
  const task = executingTask.value
  executingTask.value = null
  await doExecute(task)
}

const editTask = (task: ScheduledTask) => {
  editingTask.value = task
}
const handleCreateTask = (taskData: Record<string, unknown>) => doCreateTask(taskData)
const handleUpdateTask = (taskData: Record<string, unknown>) => {
  if (!editingTask.value) return
  doUpdateTask(editingTask.value, taskData)
}

const confirmDeleteTask = (task: ScheduledTask) => {
  deletingTask.value = task
  showDeleteDialog.value = true
}
const doDeleteTask = async () => {
  if (!deletingTask.value) return
  showDeleteDialog.value = false
  const task = deletingTask.value
  deletingTask.value = null
  await doDelete(task)
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

// ponytail: status/unit/badge/datetime formatters live in the shared
// scheduledTaskPresenters lib. getStatusCount needs the live statistics snapshot,
// so bind it here rather than passing statistics through the template.
const getStatusCount = (status: string) => getStatusCountFor(status, statistics.value)

</script>

<style scoped>
.scheduled-tasks-content {
  --app-table-content-width: 1320px;
  --app-table-min-width: 760px;
  --app-table-columns: minmax(16rem, 1fr) 7rem 8rem 10rem 7rem;
}

.task-grid {
  grid-template-columns: var(--app-table-columns);
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
