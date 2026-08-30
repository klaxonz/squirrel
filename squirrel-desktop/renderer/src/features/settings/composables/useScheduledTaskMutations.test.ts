// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useScheduledTaskMutations } from './useScheduledTaskMutations'

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  update: vi.fn(),
  del: vi.fn(),
  enable: vi.fn(),
  disable: vi.fn(),
  execute: vi.fn(),
  success: vi.fn(),
}))

vi.mock('@tanstack/vue-query', () => ({
  useMutation: (options: { mutationFn: (value: unknown) => Promise<unknown>; onSuccess?: (data: unknown, value: unknown) => void }) => ({
    mutateAsync: async (value: unknown) => {
      const result = await options.mutationFn(value)
      options.onSuccess?.(result, value)
      return result
    },
  }),
}))
vi.mock('@/shared/api', () => ({
  createTask: mocks.create,
  updateTask: mocks.update,
  deleteTask: mocks.del,
  enableTask: mocks.enable,
  disableTask: mocks.disable,
  executeTaskNow: mocks.execute,
}))

vi.mock('@/shared/components/toast/useToast', () => ({
  useToast: () => ({ success: mocks.success }),
}))
const task = {
  id: 7,
  name: '清理',
  task_type: 'cleanup',
} as never

const options = () => ({
  invalidateTasks: vi.fn(),
  scheduleInvalidate: vi.fn(),
})

describe('scheduled task mutations', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset())
  })

  it('propagates create failures without reporting a success toast', async () => {
    const error = new Error('create failed')
    mocks.create.mockRejectedValue(error)
    const mutations = useScheduledTaskMutations(options())

    await expect(mutations.handleCreateTask({ name: 'x' })).rejects.toBe(error)
    expect(mocks.success).not.toHaveBeenCalled()
  })

  it('propagates failures from update, delete, enable, disable, and execute', async () => {
    const error = new Error('mutation failed')
    mocks.update.mockRejectedValue(error)
    mocks.del.mockRejectedValue(error)
    mocks.enable.mockRejectedValue(error)
    mocks.disable.mockRejectedValue(error)
    mocks.execute.mockRejectedValue(error)
    const mutations = useScheduledTaskMutations(options())

    await expect(mutations.handleUpdateTask(task, {})).rejects.toBe(error)
    await expect(mutations.doDeleteTask(task)).rejects.toBe(error)
    await expect(mutations.enableTask(7)).rejects.toBe(error)
    await expect(mutations.disableTask(7)).rejects.toBe(error)
    await expect(mutations.executeTask(task)).rejects.toBe(error)
    expect(mocks.success).not.toHaveBeenCalled()
  })
})
