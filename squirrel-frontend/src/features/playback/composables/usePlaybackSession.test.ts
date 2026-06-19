import { beforeEach, describe, expect, it } from 'vitest'
import { isReadonly } from 'vue'
import { __resetPlaybackSessionForTests, usePlaybackSession } from './usePlaybackSession'
import type { MediaSource } from '@/features/playback/components/video-player/core'
import type { VideoPageVideo } from '@/features/playback/types/videoPlayback'

const makeSource = (overrides: Partial<MediaSource> = {}): MediaSource => ({
  src: 'https://example.test/video.m3u8',
  ...overrides,
} as MediaSource)

const makeVideo = (overrides: Partial<VideoPageVideo> = {}): VideoPageVideo => ({
  id: 'vid-1',
  title: 'A video',
  url: 'https://example.test/v/1',
  ...overrides,
} as VideoPageVideo)

describe('usePlaybackSession', () => {
  beforeEach(() => {
    __resetPlaybackSessionForTests()
  })

  describe('beginNewVideo', () => {
    it('clears stale source / video / externalError and marks loading when switching to a new video', () => {
      const session = usePlaybackSession()

      // Prime the session with an existing video so we can observe the clear.
      session.update({
        videoId: 'vid-1',
        source: makeSource(),
        video: makeVideo(),
        externalError: null,
        externalLoading: false,
      })

      session.beginNewVideo('vid-2')

      expect(session.facts.videoId).toBe('vid-2')
      expect(session.facts.source).toBeNull()
      expect(session.facts.video).toBeNull()
      expect(session.facts.externalError).toBeNull()
      expect(session.facts.externalLoading).toBe(true)
    })
  })

  describe('update', () => {
    it('applies a partial patch and leaves unmentioned fields intact', () => {
      const session = usePlaybackSession()

      session.update({
        videoId: 'vid-1',
        source: makeSource(),
        title: 'Original title',
        theme: 'light',
      })
      session.update({ title: 'Patched title' })

      expect(session.facts.title).toBe('Patched title')
      // Untouched fields survive.
      expect(session.facts.videoId).toBe('vid-1')
      expect(session.facts.source?.src).toBe('https://example.test/video.m3u8')
      expect(session.facts.theme).toBe('light')
    })
  })

  describe('isReusableFor', () => {
    it('returns true when the session already represents the video with a resolved source', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1', source: makeSource() })

      expect(session.isReusableFor('vid-1')).toBe(true)
    })

    it('returns true when the session is mid-resolution (externalLoading or externalError)', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1', source: null, externalLoading: true })

      expect(session.isReusableFor('vid-1')).toBe(true)
    })

    it('returns false for a different video id', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1', source: makeSource() })

      expect(session.isReusableFor('vid-2')).toBe(false)
    })

    it('returns false when the session has no resolvable state for the id', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1', source: null, externalError: null, externalLoading: false })

      expect(session.isReusableFor('vid-1')).toBe(false)
    })

    it('forces a refresh (returns false) for a javdb video whose actors are not resolved yet', () => {
      const session = usePlaybackSession()
      session.update({
        videoId: 'vid-1',
        source: makeSource(),
        video: makeVideo({ url: 'https://javdb.com/v/abc', actors: [] }),
      })

      expect(session.isReusableFor('vid-1')).toBe(false)
    })

    it('does not force a refresh once the javdb video has actors', () => {
      const session = usePlaybackSession()
      session.update({
        videoId: 'vid-1',
        source: makeSource(),
        video: makeVideo({ url: 'https://javdb.com/v/abc', actors: [{ name: 'Someone' }] as VideoPageVideo['actors'] }),
      })

      expect(session.isReusableFor('vid-1')).toBe(true)
    })
  })

  describe('release', () => {
    it('clears the facts when PiP is not active', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1', source: makeSource(), title: 'Was playing' })

      session.release()

      expect(session.facts.videoId).toBe('')
      expect(session.facts.source).toBeNull()
      expect(session.facts.title).toBe('')
      expect(session.facts.pictureInPicture).toBe(false)
    })

    it('keeps the facts intact when PiP is active (continuity)', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1', source: makeSource(), title: 'Was playing' })
      session.setPictureInPicture(true)

      session.release()

      expect(session.facts.videoId).toBe('vid-1')
      expect(session.facts.source?.src).toBe('https://example.test/video.m3u8')
      expect(session.facts.title).toBe('Was playing')
    })
  })

  describe('facts is readonly', () => {
    it('exposes facts as a Vue readonly view (direct writes are rejected at runtime)', () => {
      const session = usePlaybackSession()
      session.update({ videoId: 'vid-1' })

      expect(isReadonly(session.facts)).toBe(true)

      // Vue's readonly() no-ops the write in production and warns in dev; in
      // either mode the value must not change. The verbs are the only path.
      ;(session.facts as { videoId: string }).videoId = 'tampered'
      expect(session.facts.videoId).toBe('vid-1')
    })
  })

  describe('setPictureInPicture', () => {
    it('updates the pictureInPicture fact (engine events are the writer)', () => {
      const session = usePlaybackSession()
      expect(session.facts.pictureInPicture).toBe(false)

      session.setPictureInPicture(true)
      expect(session.facts.pictureInPicture).toBe(true)

      session.setPictureInPicture(false)
      expect(session.facts.pictureInPicture).toBe(false)
    })
  })
})
