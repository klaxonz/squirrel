import { reactive } from 'vue'
import type { SubtitleTrack } from '../core/types'

export type LoadingStage = 'idle' | 'fetching' | 'buffering' | 'ready'

type PlayerRuntimeStoreData = {
  // Media state
  playing: boolean
  canPlayVideo: boolean
  canPlayAudio: boolean
  seekingVideo: boolean
  seekingAudio: boolean
  loading: boolean
  loadingStage: LoadingStage
  volume: number
  muted: boolean
  currentTime: number
  duration: number
  bufferedProgress: number
  playbackRate: number
  subtitlesEnabled: boolean
  pictureInPicture: boolean
  hasStartedPlayback: boolean
  currentQuality: string | null
  currentQualityId: string | number | null
  currentSubtitle: SubtitleTrack | null
  autoplay: boolean
  autoplayNext: boolean
  loop: boolean

  // UI state
  controlsVisible: boolean
  fullscreen: boolean
}

export type PlayerRuntimeStore = PlayerRuntimeStoreData & {
  // Actions
  setPlaying: (value: boolean) => void
  setCanPlay: (type: 'video' | 'audio', value: boolean) => void
  setSeeking: (type: 'video' | 'audio', value: boolean) => void
  setLoading: (value: boolean, stage?: LoadingStage | string | null) => void
  setVolume: (value: number) => void
  setMuted: (value: boolean) => void
  toggleMute: () => void
  setCurrentTime: (value: number) => void
  setDuration: (value: number) => void
  setBufferedProgress: (value: number) => void
  setPlaybackRate: (value: number) => void
  setCurrentQuality: (value: string | null, id?: string | number | null) => void
  setCurrentQualityId: (value: string | number | null) => void
  setSubtitlesEnabled: (value: boolean) => void
  setCurrentSubtitle: (value: SubtitleTrack | null) => void
  setAutoplay: (value: boolean) => void
  setAutoplayNext: (value: boolean) => void
  setLoop: (value: boolean) => void
  setPictureInPicture: (value: boolean) => void
  setHasStartedPlayback: (value: boolean) => void
  setControlsVisible: (value: boolean) => void
  setFullscreen: (value: boolean) => void
  resetForNewVideo: () => void
}

const MAX_VOLUME = 200

export function createPlayerRuntimeStore(): PlayerRuntimeStore {
  const store = reactive<PlayerRuntimeStoreData>({
    playing: false,
    canPlayVideo: false,
    canPlayAudio: false,
    seekingVideo: false,
    seekingAudio: false,
    loading: false,
    loadingStage: 'idle',
    volume: 100,
    muted: false,
    currentTime: 0,
    duration: 0,
    bufferedProgress: 0,
    playbackRate: 1,
    subtitlesEnabled: false,
    pictureInPicture: false,
    hasStartedPlayback: false,
    currentQuality: null,
    currentQualityId: null,
    currentSubtitle: null,
    autoplay: false,
    autoplayNext: true,
    loop: false,
    controlsVisible: true,
    fullscreen: false,
  }) as PlayerRuntimeStore

  store.setPlaying = (value: boolean): void => {
    store.playing = value
  }

  store.setCanPlay = (type: 'video' | 'audio', value: boolean): void => {
    if (type === 'video') store.canPlayVideo = value
    else store.canPlayAudio = value
  }

  store.setSeeking = (type: 'video' | 'audio', value: boolean): void => {
    if (type === 'video') store.seekingVideo = value
    else store.seekingAudio = value
  }

  store.setLoading = (value: boolean, stage: LoadingStage | string | null = null): void => {
    store.loading = value
    if (stage !== null && stage !== undefined) {
      store.loadingStage = stage as LoadingStage
    }
  }

  store.setVolume = (value: number): void => {
    store.volume = Math.max(0, Math.min(MAX_VOLUME, value))
  }

  store.setMuted = (value: boolean): void => {
    store.muted = value
  }

  store.toggleMute = (): void => {
    store.muted = !store.muted
  }

  store.setCurrentTime = (value: number): void => {
    store.currentTime = value
  }

  store.setDuration = (value: number): void => {
    store.duration = value
  }

  store.setBufferedProgress = (value: number): void => {
    store.bufferedProgress = value
  }

  store.setPlaybackRate = (value: number): void => {
    store.playbackRate = value
  }

  store.setCurrentQuality = (value: string | null, id?: string | number | null): void => {
    store.currentQuality = value
    if (typeof id === 'string' || typeof id === 'number') store.currentQualityId = id
    else if (id === null) store.currentQualityId = null
  }

  store.setCurrentQualityId = (value: string | number | null): void => {
    store.currentQualityId = value
  }

  store.setSubtitlesEnabled = (value: boolean): void => {
    store.subtitlesEnabled = value
  }

  store.setCurrentSubtitle = (value: SubtitleTrack | null): void => {
    store.currentSubtitle = value
  }

  store.setAutoplay = (value: boolean): void => {
    store.autoplay = value
  }

  store.setAutoplayNext = (value: boolean): void => {
    store.autoplayNext = value
  }

  store.setLoop = (value: boolean): void => {
    store.loop = value
  }

  store.setPictureInPicture = (value: boolean): void => {
    store.pictureInPicture = value
  }

  store.setHasStartedPlayback = (value: boolean): void => {
    store.hasStartedPlayback = value
  }

  store.setControlsVisible = (value: boolean): void => {
    store.controlsVisible = value
  }

  store.setFullscreen = (value: boolean): void => {
    store.fullscreen = value
  }

  store.resetForNewVideo = (): void => {
    store.playing = false
    store.canPlayVideo = false
    store.canPlayAudio = false
    store.seekingVideo = false
    store.seekingAudio = false
    store.loading = true
    store.loadingStage = 'fetching'
    store.currentTime = 0
    store.duration = 0
    store.bufferedProgress = 0
    store.hasStartedPlayback = false
    store.pictureInPicture = false
    store.currentQuality = null
    store.currentQualityId = null
    store.currentSubtitle = null
    store.subtitlesEnabled = false
  }

  return store
}
