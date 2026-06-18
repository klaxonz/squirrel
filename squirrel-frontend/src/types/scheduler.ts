// DTOs for /api/scheduler/* — field shapes mirror the backend.
// See backend: infrastructure/scheduling/models/scheduled_task.py +
//   infrastructure/scheduling/{service,lifecycle}.py

export type ScheduledTaskUnit = 'seconds' | 'minutes' | 'hours' | 'days'
export type ScheduledTaskStatus = 'enabled' | 'disabled' | 'running' | 'error'

export interface ScheduledTask {
  id: number
  name: string
  task_type: string
  description: string | null
  interval: number
  unit: ScheduledTaskUnit | string
  start_immediately: boolean
  max_retries: number
  status: ScheduledTaskStatus | string
  is_active: boolean
  task_class: string
  task_params: Record<string, unknown>
  last_run_at: string | null
  next_run_at: string | null
  last_error: string | null
  run_count: number
  success_count: number
  error_count: number
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/** Wrapper for GET /api/scheduler/tasks. */
export interface ScheduledTaskListResponse {
  page: number
  page_size: number
  total: number
  data: ScheduledTask[]
}

/** GET /api/scheduler/status. */
export interface SchedulerStatus {
  running: boolean
  job_count: number
  last_heartbeat: string | null
  started_at: string | null
  heartbeat_age: number
  error?: string
}

/** GET /api/scheduler/statistics. */
export interface SchedulerStatistics {
  total_tasks: number
  active_tasks: number
  running_tasks: number
  error_tasks: number
  today_executions: number
}

/** GET /api/scheduler/task-classes item. */
export interface AvailableTaskClass {
  class_name: string
  name?: string
  description?: string
  params_schema?: Record<string, unknown>
}
