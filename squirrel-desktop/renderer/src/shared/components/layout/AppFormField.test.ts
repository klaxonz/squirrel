// @vitest-environment jsdom
import { createApp, defineComponent, h } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AppFormField from './AppFormField.vue'

const mountedApps: Array<ReturnType<typeof createApp>> = []

const mount = (component: ReturnType<typeof defineComponent>) => {
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(component)
  mountedApps.push(app)
  app.mount(host)
  return host
}

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('AppFormField', () => {
  it('generates an id and exposes complete control accessibility attributes', () => {
    let exposedControl: Record<string, unknown> | undefined
    const host = mount(defineComponent({
      setup() {
        return () => h(AppFormField, {
          label: 'Email',
          description: 'Used for notifications',
          error: 'Enter a valid email',
          required: true,
        }, {
          default: ({ control }: { control: Record<string, unknown> }) => {
            exposedControl = control
            return h('input', control)
          },
        })
      },
    }))

    const input = host.querySelector('input')!
    const label = host.querySelector('label')!
    const description = host.querySelector('.app-form-field__description')!
    const error = host.querySelector('.app-form-field__error')!

    expect(input.id).toMatch(/^app-form-field-/)
    expect(label.getAttribute('for')).toBe(input.id)
    expect(input.required).toBe(true)
    expect(input.getAttribute('aria-labelledby')).toBe(label.id)
    expect(input.getAttribute('aria-describedby')).toBe(`${description.id} ${error.id}`)
    expect(input.getAttribute('aria-errormessage')).toBe(error.id)
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(exposedControl?.id).toBe(input.id)
    expect(label.querySelector('[aria-hidden="true"]')?.textContent).toBe('*')
  })

  it('uses an explicit id and omits invalid state when there is no error', () => {
    const host = mount(defineComponent({
      setup() {
        return () => h(AppFormField, { id: 'display-name', label: 'Display name' }, {
          default: ({ control }: { control: Record<string, unknown> }) => h('input', control),
        })
      },
    }))

    const input = host.querySelector('input')!
    expect(input.id).toBe('display-name')
    expect(input.hasAttribute('aria-invalid')).toBe(false)
    expect(input.hasAttribute('aria-errormessage')).toBe(false)
    expect(input.hasAttribute('aria-describedby')).toBe(false)
  })

  it('includes slotted descriptions and errors in control references', () => {
    const host = mount(defineComponent({
      setup() {
        return () => h(AppFormField, { label: 'Username' }, {
          default: ({ control }: { control: Record<string, unknown> }) => h('input', control),
          description: () => 'Public identifier',
          error: () => 'Already taken',
        })
      },
    }))

    const input = host.querySelector('input')!
    expect(input.getAttribute('aria-describedby')?.split(' ')).toHaveLength(2)
    expect(input.getAttribute('aria-invalid')).toBe('true')
  })
})
