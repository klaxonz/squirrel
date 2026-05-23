export type IconName =
  | 'play'
  | 'pause'
  | 'stop'
  | 'replay'
  | 'rotate'
  | 'skipForward'
  | 'skipBackward'
  | 'previous'
  | 'prev'
  | 'next'
  | 'volumeHigh'
  | 'volumeLow'
  | 'volumeMute'
  | 'volumeOff'
  | 'fullscreen'
  | 'fullscreenExit'
  | 'widescreen'
  | 'widescreenExit'
  | 'pip'
  | 'pipExit'
  | 'settings'
  | 'markClip'
  | 'subtitles'
  | 'subtitlesOff'
  | 'quality'
  | 'speed'
  | 'autoplayNext'
  | 'loop'
  | 'check'
  | 'chevronLeft'
  | 'chevronRight'
  | 'close'
  | 'error'
  | 'loading'

export function useIcons() {
  return {
    getIcon: () => null,
    renderIcon: () => null,
    registerIcon: () => {},
    registerIcons: () => {},
    setIconSet: () => {},
    resetIcons: () => {},
    iconSet: { value: {} }
  }
}

export default useIcons
