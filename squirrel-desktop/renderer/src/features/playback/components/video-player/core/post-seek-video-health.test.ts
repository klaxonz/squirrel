import { describe, expect, it } from 'vitest'
import {
  hasPresentedVideoFrameAfterSeek,
  shouldRecoverVideoAfterSeek,
  type PostSeekVideoHealthSample,
} from './post-seek-video-health'

const healthyBase = (overrides: Partial<PostSeekVideoHealthSample> = {}): PostSeekVideoHealthSample => ({
  hasActiveVideoTrack: true,
  paused: false,
  ended: false,
  targetTime: 100,
  currentTime: 103,
  frameCallbackSupported: true,
  lastPresentedFrameMediaTime: 102.9,
  baselineDecodedFrames: 40,
  decodedFrames: 45,
  ...overrides,
})

describe('post-seek video health', () => {
  it('recovers when audio time advances but no destination video frame is presented', () => {
    expect(shouldRecoverVideoAfterSeek(healthyBase({
      lastPresentedFrameMediaTime: null,
      decodedFrames: 40,
    }))).toBe(true)
  })

  it('accepts a destination frame reported by requestVideoFrameCallback', () => {
    expect(hasPresentedVideoFrameAfterSeek(healthyBase())).toBe(true)
    expect(shouldRecoverVideoAfterSeek(healthyBase())).toBe(false)
  })

  it('does not mistake a decoded-frame counter bump for a destination frame when callbacks exist', () => {
    expect(shouldRecoverVideoAfterSeek(healthyBase({
      lastPresentedFrameMediaTime: null,
      decodedFrames: 41,
    }))).toBe(true)
  })

  it('rejects the stale pre-seek frame when seeking backward', () => {
    expect(hasPresentedVideoFrameAfterSeek(healthyBase({
      currentTime: 100.1,
      lastPresentedFrameMediaTime: 200,
    }))).toBe(false)
  })

  it('falls back to decoded frame counters when requestVideoFrameCallback is unavailable', () => {
    expect(shouldRecoverVideoAfterSeek(healthyBase({
      frameCallbackSupported: false,
      lastPresentedFrameMediaTime: null,
      decodedFrames: 41,
    }))).toBe(false)
  })

  it('does not run video recovery for pauses, audio-only media, or an unmoving clock', () => {
    const noFrame = {
      lastPresentedFrameMediaTime: null,
      decodedFrames: 40,
    }
    expect(shouldRecoverVideoAfterSeek(healthyBase({ ...noFrame, paused: true }))).toBe(false)
    expect(shouldRecoverVideoAfterSeek(healthyBase({ ...noFrame, hasActiveVideoTrack: false }))).toBe(false)
    expect(shouldRecoverVideoAfterSeek(healthyBase({ ...noFrame, currentTime: 100.2 }))).toBe(false)
  })
})
