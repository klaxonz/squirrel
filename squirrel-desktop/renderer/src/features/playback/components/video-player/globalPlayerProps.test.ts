import { beforeEach, describe, expect, it } from 'vitest'

import { buildGlobalVideoPlayerProps } from './globalPlayerProps'
import { __resetPlaybackSessionForTests, usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'

describe('buildGlobalVideoPlayerProps', () => {
  beforeEach(() => {
    __resetPlaybackSessionForTests()
  })

  it('hydrates persisted clip markers from the session video', () => {
    const session = usePlaybackSession()
    const marker = {
      id: 7,
      title: '片段',
      start_time: 12,
      end_time: 24,
    }
    session.update({
      videoId: '42',
      video: { id: 42, title: '测试视频', clip_markers: [marker] },
    })

    const props = buildGlobalVideoPlayerProps(session.facts, null)

    expect(props.videoId).toBe('42')
    expect(props.clipMarkers).toEqual([marker])
  })
})
