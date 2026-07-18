import { describe, expect, it, vi } from 'vitest'

const get = vi.fn()
const post = vi.fn()

vi.mock('@/shared/lib/request', () => ({ get, post }))

const { getSystemConfig, saveSystemConfig } = await import('./system')

describe('system config API', () => {
  it('uses the canonical trailing-slash route to avoid proxy-origin redirects', async () => {
    await getSystemConfig()

    expect(get).toHaveBeenCalledWith('/api/system/config/')
  })

  it('uses the same canonical route when saving settings', async () => {
    const payload = { enable_scheduler: true }
    await saveSystemConfig(payload)

    expect(post).toHaveBeenCalledWith('/api/system/config/', payload)
  })
})
