import { del, get, post, put } from '@/utils/request'
import type {
  ScheduledTask,
  ScheduledTaskListResponse,
  SchedulerStatus,
  SchedulerStatistics,
} from '@/types/scheduler'

export const getSchedulerStatus = async () => {
  return get<SchedulerStatus>('/api/scheduler/status')
}

export const getTaskStatistics = async () => {
  return get<SchedulerStatistics>('/api/scheduler/statistics')
}

export const getScheduledTasks = async (params: Record<string, unknown> = {}) => {
  return get<ScheduledTaskListResponse>('/api/scheduler/tasks', params)
}

export const createTask = async (taskData: Record<string, unknown>) => {
  return post<ScheduledTask>('/api/scheduler/tasks', taskData)
}

export const updateTask = async (taskId: string | number, taskData: Record<string, unknown>) => {
  return put<ScheduledTask>(`/api/scheduler/tasks/${taskId}`, taskData)
}

export const deleteTask = async (taskId: string | number) => {
  return del(`/api/scheduler/tasks/${taskId}`)
}

export const enableTask = async (taskId: string | number) => {
  return post(`/api/scheduler/tasks/${taskId}/enable`, null)
}

export const disableTask = async (taskId: string | number) => {
  return post(`/api/scheduler/tasks/${taskId}/disable`, null)
}

export const executeTaskNow = async (taskId: string | number) => {
  return post(`/api/scheduler/tasks/${taskId}/execute`, null)
}

// ponytail: task-classes shape varies by registered plugins; consumer narrows.
export const getAvailableTaskClasses = async () => {
  return get<unknown[]>('/api/scheduler/task-classes')
}

export const enableScheduler = async () => {
  return post('/api/scheduler/enable', null)
}

export const disableScheduler = async () => {
  return post('/api/scheduler/disable', null)
}
