// @vitest-environment jsdom

import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { __resetPlaybackSessionForTests, usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'
import { usePlayerStore } from '@/features/playback/stores/player'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { stopMediaOnAuthInvalidation } from './stopMediaOnAuthInvalidation'

const removeItem = vi.fn()

vi.mock('@/shared/lib/storageKeys', () => ({
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: (...args: unknown[]) => removeItem(...args),
}))

describe('stopMediaOnAuthInvalidation', () => {
  let exitPictureInPicture: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia(createPinia())
    __resetPlaybackSessionForTests()
    removeItem.mockReset()

    exitPictureInPicture = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(document, 'pictureInPictureElement', {
      configurable: true,
      get: () => null,
    })
    Object.defineProperty(document, 'exitPictureInPicture', {
      configurable: true,
      value: exitPictureInPicture,
    })
  })

  afterEach(() => {
    Object.defineProperty(document, 'pictureInPictureElement', {
      configurable: true,
      get: () => null,
    })
  })

  it('ends the video session and clears music + player wiring', () => {
    const session = usePlaybackSession()
    session.update({
      videoId: 'vid-1',
      source: { src: 'https://example.test/video.m3u8' } as never,
      title: 'Still playing',
    })
    session.setPictureInPicture(true)

    const music = useMusicPlayerStore()
    music.$patch({
      currentTrack: { hash: 'track-1', title: 'Song' } as never,
      queue: [{ hash: 'track-1', title: 'Song' }] as never,
      queueIndex: 0,
      playing: true,
      audioSrc: 'https://example.test/audio.mp3',
      resolvingUrl: true,
    })

    const playerStore = usePlayerStore()
    playerStore.playerRef = { play: vi.fn() } as never
    playerStore.target = document.createElement('div')
    playerStore.adapter = {} as never
    playerStore.handlers = { onPlay: vi.fn() }

    stopMediaOnAuthInvalidation()

    expect(session.facts.videoId).toBe('')
    expect(session.facts.source).toBeNull()
    expect(session.facts.pictureInPicture).toBe(false)
    expect(session.playback.getSnapshot().phase).toBe('idle')

    expect(music.currentTrack).toBeNull()
    expect(music.queue).toEqual([])
    expect(music.playing).toBe(false)
    expect(music.audioSrc).toBe('')
    expect(music.resolvingUrl).toBe(false)

    expect(playerStore.playerRef).toBeNull()
    expect(playerStore.target).toBeNull()
    expect(playerStore.adapter).toBeNull()
    expect(playerStore.handlers).toEqual({})
  })

  it('exits active picture-in-picture before ending the session', () => {
    const pipElement = document.createElement('video')
    Object.defineProperty(document, 'pictureInPictureElement', {
      configurable: true,
      get: () => pipElement,
    })

    const session = usePlaybackSession()
    session.update({ videoId: 'vid-pip', title: 'PiP' })
    session.setPictureInPicture(true)

    stopMediaOnAuthInvalidation()

    expect(exitPictureInPicture).toHaveBeenCalledOnce()
    expect(session.facts.videoId).toBe('')
  })
})
