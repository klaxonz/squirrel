import { describe, expect, it, vi } from 'vitest'

const get = vi.fn()
const post = vi.fn()
const put = vi.fn()
const del = vi.fn()

vi.mock('@/shared/lib/request', () => ({ get, post, put, del }))

const { createPlaylist, listPlaylists } = await import('./playlist')

describe('playlist collection API', () => {
  it('lists playlists through the canonical trailing-slash route', async () => {
    const params = { page: 1 }
    await listPlaylists(params)

    expect(get).toHaveBeenCalledWith('/api/playlist/', params)
  })

  it('creates playlists through the same canonical route', async () => {
    const payload = { name: '稍后观看', description: '待处理视频' }
    await createPlaylist(payload)

    expect(post).toHaveBeenCalledWith('/api/playlist/', payload)
  })
})
