<template>
  <AppPageShell class="scheduled-tasks-page" variant="compact" surface="operate" width="table">
    <main class="app-page-content scheduled-tasks-content">
      <AppOperatePageHeader
        title="定时任务"
        :summary="taskSummary"
        description="安排订阅同步、索引维护与后台作业。"
      >
        <template #actions>
          <Button
            type="button" size="sm"
            @click="showCreateDialog = true"
          >
            <AppIcon name="plus" class="h-4 w-4" />
            新建任务
          </Button>
          <Button
            type="button"
            text severity="secondary"
            size="sm" icon-only
            class="scheduled-tasks-refresh"
            :disabled="loading"
            title="刷新任务"
            aria-label="刷新任务"
            @click="refreshData"
          >
            <AppSpinner v-if="loading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </Button>
        </template>
      </AppOperatePageHeader>

      <div class="scheduled-tasks-filterbar">
        <AppSectionNav
          :model-value="statusFilter"
          :options="statusNavOptions"
          aria-label="任务状态"
          @change="handleStatusChange"
        />
        <span>任务状态来自当前调度器，列表会随搜索与筛选更新</span>
      </div>

      <section class="scheduled-task-list app-settings-panel" :aria-label="`${activeStatusLabel}任务`">
        <header class="scheduled-task-list__head">
          <div class="scheduled-task-list__heading">
            <h2>{{ taskPanelTitle }}</h2>
            <p aria-label="任务运行概览">
              <span>{{ statistics.active_tasks }} / {{ statistics.total_tasks }} 参与调度</span>
              <span>{{ statistics.running_tasks }} 个正在运行</span>
              <span>{{ statistics.today_executions }} 次今日执行</span>
              <span v-if="statistics.error_tasks" class="is-alert">
                {{ statistics.error_tasks }} 个异常
              </span>
            </p>
          </div>
        </header>

        <div v-if="loading && tasks.length === 0" class="scheduled-task-list__loading">
          <AppSkeleton
            v-for="i in 5"
            :key="i"
            height="5.25rem"
            rounded="var(--radius-md)"
            shimmer
          />
        </div>

        <div v-else-if="isError" class="app-page-empty app-page-empty--compact">
          <AppEmptyState variant="error" title="任务加载失败" :copy="errorMessage">
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
              <Button v-else size="sm" @click="showCreateDialog = true">
                新建任务
              </Button>
            </template>
          </AppEmptyState>
        </div>

        <template v-else>
          <article
            v-for="task in tasks"
            :key="task.id"
            class="scheduled-task-row scheduled-task-columns"
          >
            <div class="scheduled-task-row__identity">
              <div class="scheduled-task-row__glyph" aria-hidden="true">
                <AppIcon name="time" class="size-4" />
              </div>
              <div class="scheduled-task-row__copy">
                <h3>{{ getTaskDisplayName(task) }}</h3>
                <p>{{ task.description || '未添加任务说明' }}</p>
              </div>
            </div>

            <div class="scheduled-task-row__status" :data-status="task.status">
              <span class="scheduled-task-row__status-dot" aria-hidden="true" />
              <div>
                <span>状态</span>
                <strong>{{ getStatusText(task.status) }}</strong>
              </div>
            </div>

            <div class="scheduled-task-row__schedule">
              <span class="scheduled-task-row__cell-label">执行计划</span>
              <strong>{{ formatTaskInterval(task.interval, task.unit) }}</strong>
              <span>下次 {{ formatDateTime(task.next_run_at) || '尚未安排' }}</span>
            </div>

            <div class="scheduled-task-row__actions">
              <Button
                text severity="secondary"
                size="sm"
                class="scheduled-task-row__action"
                title="立即执行"
                @click="executeTask(task)"
              >
                <AppIcon name="play" class="h-4 w-4 fill-current" />
                执行
              </Button>
              <Button
                text severity="secondary"
                size="sm"
                class="scheduled-task-row__action"
                title="编辑任务"
                @click="editTask(task)"
              >
                <AppIcon name="pencil" class="h-4 w-4" />
                编辑
              </Button>
              <AppActionMenu
                :items="taskActionItems(task)"
                :trigger-label="`${getTaskDisplayName(task)} 管理操作`"
              />
            </div>
          </article>
        </template>

        <div v-if="totalPages > 1" class="scheduled-task-list__pager">
          <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
          <div>
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
import AppOperatePageHeader from '@/shared/components/layout/AppOperatePageHeader.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import TaskDialog from '@/features/settings/components/TaskDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import { Button } from '@/shared/ui/button'
import type { ScheduledTask } from '@/features/settings/types/scheduler'
import {
  formatTaskInterval,
  getTaskDisplayName,
  getStatusText,
  getStatusCount as getStatusCountFor,
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
  return `${statistics.value.total_tasks} 个任务`
})

const activeStatusLabel = computed(() => {
  return statusOptions.find(option => option.value === statusFilter.value)?.label || '全部'
})

const taskPanelTitle = computed(() => (
  statusFilter.value === 'all' ? '任务列表' : `${activeStatusLabel.value}任务`
))

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

.scheduled-tasks-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-top: var(--space-7);
  padding-bottom: var(--space-8);
}

.scheduled-tasks-refresh {
  width: 2rem;
  height: 2rem;
  color: hsl(var(--muted-foreground));
}

.scheduled-tasks-filterbar {
  display: flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  padding: 0.5rem 0.75rem;
}

.scheduled-tasks-filterbar > span {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.scheduled-task-list {
  width: 100%;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  overflow: hidden;
}

.scheduled-task-list__head {
  display: flex;
  min-height: 3.5rem;
  align-items: center;
  border-bottom: 1px solid hsl(var(--border));
  padding: 0.75rem var(--space-4);
}

.scheduled-task-list__heading {
  display: grid;
  min-width: 0;
  gap: 0.3rem;
}

.scheduled-task-list__heading h2 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 700;
}

.scheduled-task-list__heading p {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  margin: 0;
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
}

.scheduled-task-list__heading p span + span::before {
  margin-right: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.34);
  content: '·';
}

.scheduled-task-list__heading .is-alert {
  color: hsl(var(--destructive) / 0.88);
}

.scheduled-task-list__loading {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
}

.scheduled-task-columns {
  display: grid;
  grid-template-columns: minmax(18rem, 1.25fr) minmax(8rem, 0.55fr) minmax(12rem, 0.7fr) auto;
  align-items: center;
  gap: var(--space-4);
}

.scheduled-task-row {
  min-height: 5.25rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.75rem var(--space-4);
  transition: background-color var(--duration-fast) var(--ease-default);
}

.scheduled-task-row:last-of-type {
  border-bottom: 0;
}

.scheduled-task-row:hover,
.scheduled-task-row:focus-within {
  background: var(--app-row-hover-bg);
}

.scheduled-task-row__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.scheduled-task-row__glyph {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.45);
  color: hsl(var(--muted-foreground));
}

.scheduled-task-row__copy {
  display: grid;
  min-width: 0;
  gap: 0.125rem;
}

.scheduled-task-row__copy h3,
.scheduled-task-row__copy p {
  overflow: hidden;
  margin: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scheduled-task-row__copy h3 {
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 620;
}

.scheduled-task-row__copy p {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  line-height: 1.35;
}

.scheduled-task-row__status {
  display: grid;
  min-width: 7rem;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 0.5rem;
}

.scheduled-task-row__status-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.42);
}

.scheduled-task-row__status > div {
  display: flex;
  align-items: baseline;
  gap: 0.375rem;
}

.scheduled-task-row__status span:not(.scheduled-task-row__status-dot) {
  color: hsl(var(--muted-foreground) / 0.76);
  font-size: 0.6875rem;
}

.scheduled-task-row__status strong {
  color: hsl(var(--foreground) / 0.78);
  font-size: 0.75rem;
  font-weight: 600;
}

.scheduled-task-row__status[data-status='enabled'] .scheduled-task-row__status-dot {
  background: hsl(var(--success));
}

.scheduled-task-row__status[data-status='running'] .scheduled-task-row__status-dot {
  background: hsl(var(--primary));
}

.scheduled-task-row__status[data-status='error'] .scheduled-task-row__status-dot {
  background: hsl(var(--destructive) / 0.82);
}

.scheduled-task-row__status[data-status='error'] strong {
  color: hsl(var(--destructive) / 0.86);
}

.scheduled-task-row__schedule {
  display: grid;
  min-width: 0;
  gap: 0.15rem;
}

.scheduled-task-row__cell-label {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.625rem;
  font-weight: 550;
}

.scheduled-task-row__schedule strong {
  color: hsl(var(--foreground) / 0.78);
  font-size: 0.75rem;
  font-weight: 600;
}

.scheduled-task-row__schedule > span:last-child {
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scheduled-task-row__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-1);
}

.scheduled-task-row__action {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.scheduled-task-list__pager {
  display: flex;
  min-height: 3.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-top: 1px solid var(--app-hairline);
  padding: 0.625rem var(--space-4);
}

.scheduled-task-list__pager > span {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.scheduled-task-list__pager > div {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

@media (max-width: 1000px) {
  .scheduled-task-columns {
    grid-template-columns: minmax(16rem, 1fr) minmax(11rem, 0.65fr) auto;
  }

  .scheduled-task-row__status {
    display: none;
  }
}

@media (max-width: 760px) {
  .scheduled-tasks-filterbar > span {
    display: none;
  }

  .scheduled-task-columns {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .scheduled-task-row__schedule {
    display: none;
  }

  .scheduled-task-row__action {
    width: 2rem;
    padding-inline: 0;
    font-size: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .scheduled-task-row {
    transition: none;
  }
}
</style>
