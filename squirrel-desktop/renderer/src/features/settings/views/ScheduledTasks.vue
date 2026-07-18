<template>
  <AppPageShell class="scheduled-tasks-page" variant="compact" surface="operate" width="table">
    <AppToolbarFrame bordered sticky>
      <section class="scheduled-toolbar" aria-label="定时任务工具栏">
        <div class="scheduled-toolbar__leading">
          <div class="scheduled-toolbar__identity">
            <h1>定时任务</h1>
            <span>{{ taskSummary }}</span>
          </div>
          <AppSectionNav
            class="app-section-nav--optical"
            :model-value="statusFilter"
            :options="statusNavOptions"
            aria-label="任务状态"
            @change="handleStatusChange"
          />
        </div>

        <div class="scheduled-toolbar__actions">
          <Button
            type="button"
            text severity="secondary"
            size="sm" icon-only
            class="app-toolbar-control app-toolbar-icon-button"
            title="刷新任务"
            aria-label="刷新任务"
            @click="refreshData"
          >
            <AppSpinner v-if="loading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </Button>
          <Button type="button" severity="secondary" outlined size="sm" @click="showCreateDialog = true">
            <AppIcon name="plus" class="h-4 w-4" />
            新建任务
          </Button>
        </div>
      </section>
    </AppToolbarFrame>

    <main class="app-page-content scheduled-tasks-content">
      <dl class="scheduled-status-strip" aria-label="任务概览">
        <div class="scheduled-status-item">
          <dt>活跃</dt>
          <dd>{{ statistics.active_tasks }}</dd>
        </div>
        <div class="scheduled-status-item">
          <dt>运行中</dt>
          <dd>{{ statistics.running_tasks }}</dd>
        </div>
        <div class="scheduled-status-item" :class="{ 'is-alert': statistics.error_tasks > 0 }">
          <dt>异常</dt>
          <dd>{{ statistics.error_tasks }}</dd>
        </div>
        <div class="scheduled-status-item">
          <dt>今日执行</dt>
          <dd>{{ statistics.today_executions }}</dd>
        </div>
      </dl>

      <section class="scheduled-table-region" :aria-label="`${activeStatusLabel}任务`">
        <div class="app-table-shell">
          <div class="app-table-frame">
            <div class="app-table-head task-grid">
              <div>任务</div>
              <div>状态</div>
              <div>频率</div>
              <div>下次运行</div>
              <div class="text-right">操作</div>
            </div>

            <div
              v-if="loading && tasks.length === 0"
              class="app-table-loading app-content-stack app-content-stack--dense"
            >
              <AppSkeleton
                v-for="i in 5"
                :key="i"
                height="3.5rem"
                rounded="var(--radius-lg)"
                shimmer
              />
            </div>

            <div v-else-if="isError" class="app-page-empty app-page-empty--compact">
              <AppEmptyState
                variant="error"
                title="任务加载失败"
                :copy="errorMessage"
              >
                <template #actions>
                  <Button size="sm" @click="refreshData">重试</Button>
                </template>
              </AppEmptyState>
            </div>

            <div v-else-if="tasks.length === 0" class="app-page-empty app-page-empty--compact">
              <AppEmptyState
                variant="plain"
                icon="time"
                :title="hasTaskFilters ? '未找到相关任务' : '暂无定时任务'"
                :copy="hasTaskFilters ? '调整筛选条件后再试。' : '创建任务后会显示在这里。'"
              >
                <template #actions>
                  <Button
                    v-if="hasTaskFilters"
                    size="sm"
                    severity="secondary"
                    @click="clearTaskFilters"
                  >
                    清空筛选
                  </Button>
                  <Button
                    v-else
                    size="sm"
                    @click="showCreateDialog = true"
                  >
                    新建任务
                  </Button>
                </template>
              </AppEmptyState>
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
                  <p v-if="task.description" class="mt-1 line-clamp-1 text-xs text-muted-foreground">
                    {{ task.description }}
                  </p>
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
                  <Button
                    text severity="secondary"
                    size="sm" icon-only
                    class="text-muted-foreground"
                    title="立即执行"
                    @click="executeTask(task)"
                  >
                    <AppIcon name="play" class="h-4 w-4 fill-current" />
                  </Button>
                  <Button
                    text severity="secondary"
                    size="sm" icon-only
                    class="text-muted-foreground"
                    title="编辑"
                    @click="editTask(task)"
                  >
                    <AppIcon name="pencil" class="h-4 w-4" />
                  </Button>
                  <AppActionMenu
                    :items="taskActionItems(task)"
                    :trigger-label="`${task.name} 管理操作`"
                  />
                </div>
              </div>
            </div>

            <div v-if="totalPages > 1" class="app-table-pager">
              <span class="text-xs text-muted-foreground">
                第 {{ currentPage }} / {{ totalPages }} 页
              </span>
              <div class="flex items-center gap-2">
                <Button
                  severity="secondary" outlined
                  size="sm"
                  :disabled="currentPage <= 1"
                  @click="goToPage(currentPage - 1)"
                >
                  上一页
                </Button>
                <Button
                  severity="secondary" outlined
                  size="sm"
                  :disabled="currentPage >= totalPages"
                  @click="goToPage(currentPage + 1)"
                >
                  下一页
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>
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
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import TaskDialog from '@/features/settings/components/TaskDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import { Button } from '@/shared/ui/button'
import { Badge } from '@/shared/ui/badge'
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
import { useUIStore } from '@/shared/stores/ui'

const SEARCH_SCOPE = 'scheduled-tasks'
const uiStore = useUIStore()
const currentPage = ref(1)
const searchQuery = computed(() => uiStore.getSearchQuery(SEARCH_SCOPE))
const searchQueryDebounced = ref(searchQuery.value)
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

const taskActionItems = (task: ScheduledTask) => [
  task.is_active
    ? { label: '暂停任务', appIcon: 'pause' as const, command: () => disableTask(task.id) }
    : { label: '恢复任务', appIcon: 'sync' as const, command: () => enableTask(task.id) },
  { separator: true },
  {
    label: '删除任务',
    appIcon: 'trash' as const,
    danger: true,
    command: () => confirmDeleteTask(task),
  },
]

const hasTaskFilters = computed(() => Boolean(searchQuery.value || statusFilter.value !== 'all'))

const clearTaskFilters = () => {
  statusFilter.value = 'all'
  currentPage.value = 1
  uiStore.triggerSearch(SEARCH_SCOPE, '')
  searchQueryDebounced.value = ''
}

const taskSummary = computed(() => {
  const stats = statistics.value
  return `${stats.total_tasks} 个任务，${stats.active_tasks} 个正在参与调度`
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
] as const

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
  isError,
  errorMessage,
  refreshData,
  invalidateTasks,
} = useScheduledTaskQueries({
  page: currentPage,
  search: searchQueryDebounced,
  status: statusFilter,
})

const statusNavOptions = computed(() => statusOptions.map(option => ({
  ...option,
  badge: getStatusCountFor(option.value, statistics.value),
})))

const handleStatusChange = (value: string | number) => {
  setStatusFilter(String(value))
}

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

</script>

<style scoped>
.scheduled-tasks-page {
  --app-page-max-width: var(--app-content-table-max);
}

.scheduled-toolbar {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.scheduled-toolbar__leading {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-5);
}

.scheduled-toolbar__identity {
  display: flex;
  min-width: 0;
  flex: none;
  align-items: baseline;
  gap: var(--space-2);
}

.scheduled-toolbar__identity h1 {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1rem;
  font-weight: 650;
}

.scheduled-toolbar__identity span {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.scheduled-toolbar__actions {
  display: flex;
  min-width: 0;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
}

.scheduled-tasks-content {
  --app-table-min-width: 860px;
  --app-table-columns: minmax(24rem, 1fr) 7rem 9rem 11rem 7rem;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding-top: var(--space-4);
}

.scheduled-status-strip {
  display: flex;
  min-height: 2.5rem;
  align-items: center;
  margin: 0;
  border-bottom: 1px solid var(--app-hairline);
}

.scheduled-status-item {
  display: flex;
  align-items: baseline;
  gap: 0.375rem;
  margin: 0;
}

.scheduled-status-item + .scheduled-status-item {
  margin-left: var(--space-5);
  border-left: 1px solid var(--app-hairline);
  padding-left: var(--space-5);
}

.scheduled-status-item dt {
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
  font-weight: 550;
  line-height: 1.25;
}

.scheduled-status-item dd {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
}

.scheduled-status-item.is-alert dd {
  color: hsl(var(--destructive));
}

.scheduled-table-region {
  min-width: 0;
}

.scheduled-table-region .app-table-row {
  min-height: 4.25rem;
}

.task-grid {
  grid-template-columns: var(--app-table-columns);
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1180px) {
  .scheduled-toolbar__identity span {
    display: none;
  }
}
</style>
