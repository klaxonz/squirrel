// @vitest-environment jsdom
import { createApp, defineComponent, h } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AppContentRow from './AppContentRow.vue'
import AppMediaItem from './AppMediaItem.vue'
import AppSelectableListItem from './AppSelectableListItem.vue'

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

describe('AppContentRow', () => {
  it('keeps primary activation and independent actions as sibling buttons', () => {
    const activate = vi.fn()
    const action = vi.fn()
    const host = mount(defineComponent({
      setup() {
        return () => h(AppContentRow, {
          ariaLabel: 'Open item',
          onActivate: activate,
        }, {
          default: () => h('span', 'Item title'),
          actions: () => h('button', { class: 'secondary-action', onClick: action }, 'More'),
        })
      },
    }))

    const primary = host.querySelector('.app-content-row__primary') as HTMLButtonElement
    const secondary = host.querySelector('.secondary-action') as HTMLButtonElement

    expect(primary.type).toBe('button')
    expect(primary.getAttribute('aria-label')).toBe('Open item')
    expect(primary.contains(secondary)).toBe(false)
    expect(primary.parentElement).toBe(secondary.parentElement?.parentElement)

    secondary.click()
    expect(action).toHaveBeenCalledOnce()
    expect(activate).not.toHaveBeenCalled()

    primary.click()
    expect(activate).toHaveBeenCalledOnce()
  })

  it('labels its primary control from row content and exposes selected state', () => {
    const host = mount(defineComponent({
      setup() {
        return () => h(AppContentRow, { selected: true, selectable: true }, {
          default: () => h('span', 'Readable title'),
        })
      },
    }))

    const primary = host.querySelector('.app-content-row__primary')!
    const content = host.querySelector('.app-content-row__content')!
    expect(primary.getAttribute('aria-labelledby')).toBe(content.id)
    expect(primary.getAttribute('aria-pressed')).toBe('true')
  })
})

describe('AppMediaItem', () => {
  it('composes media, body, metadata, and independent actions', () => {
    const host = mount(defineComponent({
      setup() {
        return () => h(AppMediaItem, { ariaLabel: 'Open episode' }, {
          media: () => h('img', { alt: '' }),
          default: () => h('strong', 'Episode title'),
          meta: () => '12 minutes',
          actions: () => h('button', 'Download'),
        })
      },
    }))

    expect(host.querySelector('.app-media-item__media img')).not.toBeNull()
    expect(host.querySelector('.app-media-item__body')?.textContent).toContain('Episode title')
    expect(host.querySelector('.app-media-item__meta')?.textContent).toBe('12 minutes')
    expect(host.querySelector('.app-content-row__actions button')?.textContent).toBe('Download')
  })
})

describe('AppSelectableListItem', () => {
  it('preserves click activation without role-button nesting', () => {
    const click = vi.fn()
    const host = mount(defineComponent({
      setup() {
        return () => h(AppSelectableListItem, {
          selected: true,
          ariaLabel: 'Select account',
          onClick: click,
        }, {
          default: () => [h('span', 'Account'), h('button', { class: 'edit' }, 'Edit')],
        })
      },
    }))

    const row = host.querySelector('.app-selectable-list-item')!
    const primary = host.querySelector('.app-content-row__primary') as HTMLButtonElement
    const edit = host.querySelector('.edit') as HTMLButtonElement

    expect(row.hasAttribute('role')).toBe(false)
    expect(primary.getAttribute('aria-pressed')).toBe('true')
    expect(primary.contains(edit)).toBe(false)
    edit.click()
    expect(click).not.toHaveBeenCalled()
    primary.click()
    expect(click).toHaveBeenCalledOnce()
  })
})
