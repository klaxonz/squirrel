import { useMutation } from '@tanstack/vue-query'
import { useToast } from '@/shared/components/toast/useToast'
import type { ScheduledTask } from '@/features/settings/types/scheduler'
import {
  createTask as apiCreateTask,
  deleteTask as apiDeleteTask,
  disableTask as apiDisableTask,
  enableTask as apiEnableTask,
  executeTaskNow as apiExecuteTaskNow,
  updateTask as apiUpdateTask,
} from '@/shared/api'

/**
 * Scheduled-task write operations (create / update / delete / enable / disable
 * / execute) as vue-query mutations, with toasts + cache invalidation wired in.
 *
 * Each mutation's onSuccess toasts the user-facing result and invalidates the
 * task query family (via the injected `invalidateTasks`) so the list/stats
 * re-fetch on next read. Create/update/delete additionally call injected
 * `onCreated` / `onUpdated` / `onDeleted` callbacks so the host can close the
 * relevant dialog — the composable doesn't own dialog visibility.
 *
 * `execute` is special: the backend needs a beat to flip the row to "running",
 * so onSuccess toasts + schedules a single delayed invalidation rather than an
 * immediate refetch (which would briefly show stale state). The caller owns the
 * delayed-invalidation timer via the injected `scheduleInvalidate`.
 *
 * Extracted from ScheduledTasks.vue so the six mutations + their toast/invalidate
 * contract live in one place rather than interleaved with dialog state.
 */
export interface UseScheduledTaskMutationsOptions {
  invalidateTasks: () => void
  /** Scheduled (delayed) invalidation after an execute; host owns the timer. */
  scheduleInvalidate: (delayMs: number) => void
  onCreated?: () => void
  onUpdated?: () => void
}

export interface UseScheduledTaskMutationsReturn {
  handleCreateTask: (taskData: Record<string, unknown>) => Promise<void>
  handleUpdateTask: (task: ScheduledTask, taskData: Record<string, unknown>) => Promise<void>
  doDeleteTask: (task: ScheduledTask) => Promise<void>
  enableTask: (id: string | number) => void
  disableTask: (id: string | number) => void
  executeTask: (task: ScheduledTask) => Promise<void>
}

export function useScheduledTaskMutations(
  options: UseScheduledTaskMutationsOptions,
): UseScheduledTaskMutationsReturn {
  const { invalidateTasks, scheduleInvalidate, onCreated, onUpdated } = options
  const toast = useToast()

  const createMutation = useMutation({
    mutationFn: (taskData: Record<string, unknown>) => apiCreateTask(taskData),
    onSuccess: () => {
      toast.success('任务创建成功')
      onCreated?.()
      invalidateTasks()
    },
  })

  const handleCreateTask = async (taskData: Record<string, unknown>) => {
    await createMutation.mutateAsync(taskData).catch(() => {
      /* toast handled by MutationCache */
    })
  }

  const updateMutation = useMutation({
    mutationFn: ({ task, taskData }: { task: ScheduledTask; taskData: Record<string, unknown> }) =>
      apiUpdateTask(task.id, taskData),
    onSuccess: () => {
      toast.success('任务已更新')
      onUpdated?.()
      invalidateTasks()
    },
  })

  const handleUpdateTask = async (task: ScheduledTask, taskData: Record<string, unknown>) => {
    await updateMutation.mutateAsync({ task, taskData }).catch(() => {})
  }

  const deleteMutation = useMutation({
    mutationFn: (task: ScheduledTask) => apiDeleteTask(task.id),
    onSuccess: () => {
      toast.success('任务已删除')
      invalidateTasks()
    },
  })

  const doDeleteTask = async (task: ScheduledTask) => {
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

  const executeMutation = useMutation({
    mutationFn: (task: ScheduledTask) => apiExecuteTaskNow(task.id),
    onSuccess: (_data, task) => {
      toast.success(`任务「${task.name}」已开始执行`)
      scheduleInvalidate(800)
    },
  })

  const executeTask = async (task: ScheduledTask) => {
    await executeMutation.mutateAsync(task).catch(() => {})
  }

  return {
    handleCreateTask,
    handleUpdateTask,
    doDeleteTask,
    enableTask,
    disableTask,
    executeTask,
  }
}
