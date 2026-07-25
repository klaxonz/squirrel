import { describe, expect, it } from 'vitest'

import {
  consumeVideoPlaybackSeed,
  peekVideoPlaybackSeed,
  rememberVideoPlaybackSeed,
} from './videoPlaybackSeed'

describe('videoPlaybackSeed', () => {
  it('stores the full list payload so resolve can start without detail', () => {
    rememberVideoPlaybackSeed({
      id: 42,
      title: 'Never Gonna Give You Up',
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      thumbnail: 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
    })

    expect(peekVideoPlaybackSeed(42)).toEqual(expect.objectContaining({
      id: 42,
      title: 'Never Gonna Give You Up',
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    }))

    expect(consumeVideoPlaybackSeed('42')).toEqual(expect.objectContaining({
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    }))
    expect(peekVideoPlaybackSeed(42)).toBeNull()
  })

  it('ignores empty ids so accidental bare clicks do not poison the map', () => {
    rememberVideoPlaybackSeed({ id: '', url: 'https://www.youtube.com/watch?v=x' })
    rememberVideoPlaybackSeed(null)
    expect(peekVideoPlaybackSeed('')).toBeNull()
  })
})
