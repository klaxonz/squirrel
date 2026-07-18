import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

describe('history item interaction contract', () => {
  const item = read('./HistoryItem.vue')
  const page = read('../../views/History.vue')

  it('keeps delete control discoverable without hover when motion or hover is limited', () => {
    expect(item).toContain('history-item__delete')
    expect(item).toMatch(/@media \(hover: none\),\s*\(prefers-reduced-motion: reduce\)/)
    expect(item).toContain('title="删除此条历史"')
    expect(item).toContain('aria-label="删除此条历史"')
    expect(item).toContain(".history-item__open:focus-visible")
  })

  it('exposes a stable DOM contract for filters and automation', () => {
    expect(item).toContain('class="history-item"')
    expect(item).toContain('data-history-item')
    expect(item).toContain('data-unfinished')
    expect(item).toContain('data-history-id')
    expect(page).toContain('class="history-groups"')
    expect(page).toContain('data-history-list')
    expect(page).toContain('data-history-mode')
    expect(page).toMatch(/HistoryItem/)
  })
})
