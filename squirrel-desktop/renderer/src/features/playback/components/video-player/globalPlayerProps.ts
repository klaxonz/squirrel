import type { IPlayerAdapter } from './core'
import type { ThemeName } from './themes'
import type { VideoClipMarker } from '@/features/video/types/videoClipMarker'
import type { PlaybackSessionFacts } from '@/features/playback/composables/usePlaybackSession'

/**
 * Project session-owned facts into the public VideoPlayer prop contract.
 *
 * Clip markers deliberately derive from `facts.video.clip_markers`: keeping a
 * second marker array on the session caused persisted markers to disappear
 * whenever the player mounted from freshly loaded video details.
 */
export const buildGlobalVideoPlayerProps = (
  facts: Readonly<PlaybackSessionFacts>,
  adapter: IPlayerAdapter | null,
) => ({
  source: facts.source,
  subtitles: facts.subtitles,
  clipMarkers: (facts.video?.clip_markers || []) as unknown as VideoClipMarker[],
  videoId: facts.videoId || null,
  title: facts.title,
  uploader: facts.uploader,
  initialTime: facts.initialTime,
  hasPrev: facts.hasPrev,
  hasNext: facts.hasNext,
  widescreen: facts.widescreen,
  adapter,
  theme: (facts.theme || 'dark') as ThemeName,
  playlistEntries: facts.playlist,
  playlistIndex: facts.playlistIndex,
})
