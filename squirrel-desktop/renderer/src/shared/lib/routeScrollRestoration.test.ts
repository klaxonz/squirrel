// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  applyRouteScrollPositions,
  collectRouteScrollPositions,
} from './routeScrollRestoration'

const createScrollArea = (key: string, scrollTop: number) => {
  const element = document.createElement('div')
  element.dataset.routeScroll = key
  element.scrollTop = scrollTop
  return element
}

describe('route scroll restoration', () => {
  it('captures every named scroll area in a page', () => {
    const root = document.createElement('div')
    root.append(createScrollArea('main', 720), createScrollArea('workbench-main', 1380))

    expect(collectRouteScrollPositions(root)).toEqual({
      main: 720,
      'workbench-main': 1380,
    })
  })

  it('restores outer and nested list positions together', () => {
    const root = document.createElement('div')
    const main = createScrollArea('main', 0)
    const nested = createScrollArea('subscribed-content', 0)
    root.append(main, nested)

    expect(applyRouteScrollPositions(root, {
      main: 640,
      'subscribed-content': 1920,
    })).toBe(true)
    expect(main.scrollTop).toBe(640)
    expect(nested.scrollTop).toBe(1920)
  })

  it('asks the caller to retry while an async scroll area is not mounted', () => {
    const root = document.createElement('div')
    root.append(createScrollArea('main', 0))

    expect(applyRouteScrollPositions(root, {
      main: 300,
      'workbench-main': 900,
    })).toBe(false)
  })
})
