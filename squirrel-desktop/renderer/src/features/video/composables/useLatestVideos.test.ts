import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useLatestVideos } from './useLatestVideos'

const { getVideoListMock } = vi.hoisted(() => ({
  getVideoListMock: vi.fn(),
}))

vi.mock('@/shared/api', () => ({
  getVideoList: getVideoListMock,
}))

const item = (id: number, overrides: Record<string, unknown> = {}) => ({
  id,
  title: `视频 ${id}`,
  url: `https://example.test/v/${id}`,
  thumbnail: null,
  duration: 100,
  last_position: 0,
  is_read: false,
  interaction_type: null,
  uploaded_at: '2026-01-01 00:00:00',
  created_at: '2026-01-01 00:00:00',
  subscriptions: [],
  actors: [],
  ...overrides,
})

describe('useLatestVideos', () => {
  beforeEach(() => {
    getVideoListMock.mockReset()
  })

  it('keeps the server-provided is_read instead of forcing it to false', async () => {
    getVideoListMock.mockResolvedValue({
      data: [item(1, { is_read: true, last_position: 42 })],
      next_cursor: null,
    })
    const list = useLatestVideos()

    await list.loadMore()

    expect(list.videos.value).toHaveLength(1)
    expect(list.videos.value[0]).toMatchObject({ is_read: true, last_position: 42 })
  })
})
