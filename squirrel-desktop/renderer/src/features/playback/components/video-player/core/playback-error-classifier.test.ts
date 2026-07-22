import { describe, expect, it } from 'vitest'
import { classifyPlaybackError } from './playback-error-classifier'

describe('classifyPlaybackError', () => {
  it.each([
    ['NETWORK_TIMEOUT', 'network'],
    ['HTTP_403', 'authorization'],
    ['MEDIA_NOT_SUPPORTED', 'source'],
    ['STALL_DETECTED', 'buffer'],
    ['CAPABILITY_MISSING', 'capability'],
    ['MEDIA_DECODE_ERROR', 'decode'],
    ['POST_SEEK_VIDEO_FROZEN', 'decode'],
    ['SHAKA_3016', 'media'],
    ['RESOLVE_FAILED', 'unknown'],
  ] as const)('classifies %s as %s', (code, kind) => {
    expect(classifyPlaybackError({ code, message: '' })).toBe(kind)
  })

  it('uses the message when a library exposes only a numeric code', () => {
    expect(classifyPlaybackError({ code: '3016', message: 'Response returned HTTP 403' }))
      .toBe('authorization')
  })
})
