import { computed, type ComputedRef } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { queryKeys } from '@/shared/lib/queryClient'
import {
  getAvailableTaskClasses,
  getScheduledTasks,
  getTaskStatistics,
} from '@/shared/api'
import type { ScheduledTask, ScheduledTaskListResponse, SchedulerStatistics } from '@/features/settings/types/scheduler'

const PAGE_SIZE = 15

/**
 * vue-query data layer for the scheduled-tasks view.
 *
 * Owns the three loaders (statistics / task classes / paged task list) and
 * their derived projections, plus the invalidation + full-refresh entry points.
 * The list queryKey is reactive on page/search/status so vue-query refetches
 * automatically — there's no parallel mutable ref, so there's no stale-data
 * window between the cache and a local copy.
 *
 * `invalidateTasks` is returned so the mutations composable can mark the task
 * query family stale after writes (preferred over refetch — concurrent
 * invalidations dedupe and respect staleTime).
 *
 * Extracted from ScheduledTasks.vue so the query wiring + the derived
 * projections live in one place rather than interleaved with mutations + dialog
 * state.
 */
export interface UseScheduledTaskQueriesOptions {
  page: ComputedRef<number> | { value: number }
  search: ComputedRef<string> | { value: string }
  status: ComputedRef<string> | { value: string }
}

export interface UseScheduledTaskQueriesReturn {
  statistics: ComputedRef<SchedulerStatistics>
  taskClasses: ComputedRef<Record<string, unknown>>
  tasks: ComputedRef<ScheduledTask[]>
  totalPages: ComputedRef<number>
  loading: ComputedRef<boolean>
  refreshData: () => Promise<void>
  invalidateTasks: () => void
}

export function useScheduledTaskQueries(
  options: UseScheduledTaskQueriesOptions,
): UseScheduledTaskQueriesReturn {
  const { page, search, status } = options
  const queryClient = useQueryClient()

  const statsQuery = useQuery({
    queryKey: queryKeys.tasks.statistics,
    queryFn: () => getTaskStatistics(),
  })

  const classesQuery = useQuery({
    queryKey: queryKeys.tasks.classes,
    queryFn: () => getAvailableTaskClasses(),
  })

  const tasksQuery = useQuery({
    queryKey: computed(() =>
      queryKeys.tasks.list({ page: page.value, search: search.value || '', status: status.value }),
    ),
    queryFn: () =>
      getScheduledTasks({
        page: page.value,
        page_size: PAGE_SIZE,
        search: search.value || undefined,
        status: status.value === 'all' ? undefined : status.value,
      }) as Promise<ScheduledTaskListResponse>,
  })

  const statistics = computed<SchedulerStatistics>(() => statsQuery.data.value ?? {
    total_tasks: 0,
    active_tasks: 0,
    running_tasks: 0,
    error_tasks: 0,
    today_executions: 0,
  })
  const taskClasses = computed(() => classesQuery.data.value ?? {})
  const tasks = computed<ScheduledTask[]>(() => tasksQuery.data.value?.data ?? [])
  const totalPages = computed(() => {
    const total = tasksQuery.data.value?.total ?? 0
    return Math.max(1, Math.ceil(total / PAGE_SIZE))
  })
  // Skeletons show on first load only (isLoading); background refetches keep
  // the prior list visible rather than flashing the skeleton.
  const loading = computed(() => tasksQuery.isLoading.value)

  const refreshData = async () => {
    await Promise.all([
      statsQuery.refetch(),
      classesQuery.refetch(),
      tasksQuery.refetch(),
    ])
  }

  const invalidateTasks = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.tasks.all })
  }

  return {
    statistics,
    taskClasses,
    tasks,
    totalPages,
    loading,
    refreshData,
    invalidateTasks,
  }
}
