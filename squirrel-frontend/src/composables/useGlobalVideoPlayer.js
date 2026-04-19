import { nextTick, reactive, shallowRef } from 'vue'

const createDefaultSession = () => ({
  active: false,
  target: null,
  source: null,
  subtitles: [],
  clipMarkers: [],
  title: '',
  initialTime: 0,
  hasPrev: false,
  hasNext: false,
  externalError: null,
  externalLoading: false,
  adapter: null,
  theme: 'dark',
  widescreen: false,
  currentVideoId: '',
  videoSnapshot: null,
  relatedVideos: [],
  loadingRelated: false,
  pictureInPicture: false,
  handlers: {
    onPlay: null,
    onPause: null,
    onEnded: null,
    onTimeUpdate: null,
    onPrev: null,
    onNext: null,
    onRetry: null,
    onWidescreenChange: null,
    onClipMarkerSelect: null,
    onClipMarkersUpdated: null,
  },
})

const session = reactive(createDefaultSession())
const playerRef = shallowRef(null)

const applySessionPayload = (payload = {}) => {
  if (!payload || typeof payload !== 'object') return

  const {
    handlers,
    target,
    ...rest
  } = payload

  Object.assign(session, rest)

  if (payload.active !== false) {
    session.active = true
  }

  if (target !== undefined) {
    session.target = target
  }

  if (handlers && typeof handlers === 'object') {
    Object.assign(session.handlers, handlers)
  }
}

const registerPlayerInstance = (instance) => {
  playerRef.value = instance
}

const seekPlayer = async (time) => {
  const nextTime = Number(time)
  if (!Number.isFinite(nextTime)) return false

  try {
    playerRef.value?.seek?.(nextTime)
    return true
  } catch {
    return false
  }
}

const playPlayer = async () => {
  try {
    await playerRef.value?.play?.()
    return true
  } catch {
    return false
  }
}

const focusPlayer = async () => {
  await nextTick()
  window.setTimeout(() => {
    try {
      const rootEl = playerRef.value?.$el
      const containerEl = rootEl instanceof HTMLElement ? rootEl : null
      const playerContainer = containerEl?.classList?.contains('sp-player')
        ? containerEl
        : containerEl?.querySelector('.sp-player')

      if (playerContainer && typeof playerContainer.focus === 'function') {
        playerContainer.focus({ preventScroll: true })
      }
    } catch {}
  }, 100)
}

const clearGlobalVideoPlayerSession = () => {
  Object.assign(session, createDefaultSession())
  playerRef.value = null
}

export function useGlobalVideoPlayer() {
  const activateGlobalVideoPlayerSession = (payload = {}) => {
    applySessionPayload(payload)
  }

  const updateGlobalVideoPlayerSession = (payload = {}) => {
    applySessionPayload(payload)
  }

  const registerGlobalVideoPlayerTarget = (element) => {
    session.target = element
  }

  const unregisterGlobalVideoPlayerTarget = (element = null) => {
    if (!element || session.target === element) {
      session.target = null
    }
  }

  const setGlobalVideoPlayerPictureInPicture = (value) => {
    session.pictureInPicture = !!value
  }

  const setGlobalVideoPlayerCurrentVideoId = (videoId) => {
    session.currentVideoId = String(videoId || '')
  }

  return {
    globalVideoPlayerSession: session,
    activateGlobalVideoPlayerSession,
    updateGlobalVideoPlayerSession,
    clearGlobalVideoPlayerSession,
    registerGlobalVideoPlayerTarget,
    unregisterGlobalVideoPlayerTarget,
    registerGlobalVideoPlayerInstance: registerPlayerInstance,
    focusGlobalVideoPlayer: focusPlayer,
    seekGlobalVideoPlayer: seekPlayer,
    playGlobalVideoPlayer: playPlayer,
    setGlobalVideoPlayerPictureInPicture,
    setGlobalVideoPlayerCurrentVideoId,
  }
}
