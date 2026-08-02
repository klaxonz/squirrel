// @vitest-environment jsdom
import { createApp, defineComponent, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TaskDialog from './TaskDialog.vue'

vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: defineComponent({ template: '<span aria-hidden="true" />' }),
}))

const passthrough = (tag = 'div') => defineComponent({
  inheritAttrs: false,
  template: `<${tag} v-bind="$attrs"><slot /></${tag}>`,
})

const DialogStub = defineComponent({ template: '<div><slot /></div>' })
const apps: Array<ReturnType<typeof createApp>> = []

const mountDialog = (props: Record<string, unknown> = {}) => {
  const host = document.createElement('div')
  const save = vi.fn()
  document.body.append(host)
  const app = createApp(TaskDialog, {
    taskClasses: {
      ExampleTask: { name: '示例任务', description: '用于测试', module: '系统' },
    },
    onSave: save,
    ...props,
  })
  for (const name of ['Dialog', 'DialogContent', 'DialogFooter', 'DialogHeader']) {
    app.component(name, DialogStub)
  }
  app.component('DialogTitle', passthrough('h2'))
  apps.push(app)
  app.mount(host)
  return { host, save }
}

const setInput = async (input: HTMLInputElement | HTMLTextAreaElement, value: string) => {
  input.value = value
  input.dispatchEvent(new Event('input', { bubbles: true }))
  await nextTick()
}

afterEach(() => {
  apps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('TaskDialog form', () => {
  it('binds the footer submit button to the form and blocks invalid values', async () => {
    const { save } = mountDialog()
    await nextTick()

    const submit = document.querySelector<HTMLButtonElement>('button[type="submit"]')!
    expect(submit.getAttribute('form')).toBe('task-dialog-form')
    submit.click()
    await nextTick()

    expect(save).not.toHaveBeenCalled()
    const name = document.querySelector<HTMLInputElement>('#task-dialog-name')!
    expect(name.getAttribute('aria-invalid')).toBe('true')
    expect(name.getAttribute('aria-errormessage')).toBe('task-dialog-name-error')
  })

  it('associates JSON errors and emits normalized valid task data', async () => {
    const { save } = mountDialog({
      task: {
        name: '已有任务',
        task_class: 'ExampleTask',
        interval: 10,
        unit: 'minutes',
        max_retries: 0,
        task_params: {},
      },
    })
    await nextTick()

    const retries = document.querySelector<HTMLInputElement>('#task-dialog-retries')!
    expect(retries.value).toBe('0')
    const params = document.querySelector<HTMLTextAreaElement>('#task-dialog-params')!
    await setInput(params, '[]')
    expect(params.getAttribute('aria-invalid')).toBe('true')
    expect(document.querySelector('#task-dialog-params-error')?.textContent).toContain('JSON 对象')

    await setInput(params, '{"mode":"full"}')
    document.querySelector<HTMLButtonElement>('button[type="submit"]')!.click()
    await nextTick()

    expect(save).toHaveBeenCalledWith(expect.objectContaining({
      name: '已有任务',
      task_class: 'ExampleTask',
      interval: 10,
      unit: 'minutes',
      max_retries: 0,
      task_params: { mode: 'full' },
    }))
  })
})
