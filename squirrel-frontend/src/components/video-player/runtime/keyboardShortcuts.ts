export interface KeyboardShortcutsConfig {
  enabled?: boolean
  playPause?: string
  fullscreen?: string
  rotate?: string
  seekBackward?: string
  seekForward?: string
  volumeUp?: string
  volumeDown?: string
  markPoint?: string
  markSegmentStart?: string
  markSegmentFinish?: string
  cancelSegment?: string
  prevVideo?: string
  nextVideo?: string
  toggleSubtitles?: string
  toggleStats?: string
}

export const DEFAULT_SHORTCUTS: Required<KeyboardShortcutsConfig> = {
  enabled: true,
  playPause: ' ',
  fullscreen: 'f',
  rotate: 'r',
  seekBackward: 'ArrowLeft',
  seekForward: 'ArrowRight',
  volumeUp: 'ArrowUp',
  volumeDown: 'ArrowDown',
  markPoint: 'm',
  markSegmentStart: 'M',
  markSegmentFinish: 'M',
  cancelSegment: 'Escape',
  prevVideo: 'p',
  nextVideo: 'n',
  toggleSubtitles: 'c',
  toggleStats: 's',
}
