import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'

export type VideoDensity = 'compact' | 'comfortable' | 'large'
type VideoViewMode = 'grid' | 'list'
type VideoViewPreference = { viewMode: VideoViewMode; density: VideoDensity }
type SidebarStateOptions = { persist?: boolean }

export const useUIStore = defineStore('ui', () => {
  const SIDEBAR_OPEN_KEY = 'ui.sidebarOpen'
  const readPersistedSidebarOpen = (): boolean => {
    if (typeof localStorage === 'undefined') return true
    return localStorage.getItem(SIDEBAR_OPEN_KEY) !== 'false'
  }
  const isSidebarOpen = ref(readPersistedSidebarOpen())
  const isVideoWidescreen = ref(false)
  const isVideoSidebarOpen = ref(true)
  const searchQueries = reactive<Record<string, string>>({})
  const searchTriggers = reactive<Record<string, number>>({})
  const homeSearchMode = ref<'local' | 'remote'>('local')

  const VIEW_MODE_KEY = 'ui.viewMode'
  const readPersistedViewMode = (): VideoViewMode => {
    if (typeof localStorage === 'undefined') return 'grid'
    return localStorage.getItem(VIEW_MODE_KEY) === 'list' ? 'list' : 'grid'
  }
  const viewMode = ref<'grid' | 'list'>(readPersistedViewMode())
  const VIDEO_DENSITY_KEY = 'ui.videoDensity'
  const readPersistedVideoDensity = (): VideoDensity => {
    if (typeof localStorage === 'undefined') return 'comfortable'
    const value = localStorage.getItem(VIDEO_DENSITY_KEY)
    return value === 'compact' || value === 'large' ? value : 'comfortable'
  }
  const videoDensity = ref<VideoDensity>(readPersistedVideoDensity())
  const VIDEO_VIEW_PREFERENCES_KEY = 'ui.videoViewPreferences'
  const readVideoViewPreferences = (): Record<string, VideoViewPreference> => {
    if (typeof localStorage === 'undefined') return {}
    try {
      const parsed = JSON.parse(localStorage.getItem(VIDEO_VIEW_PREFERENCES_KEY) || '{}') as Record<string, Partial<VideoViewPreference>>
      return Object.fromEntries(Object.entries(parsed).flatMap(([key, value]) => {
        const validMode = value.viewMode === 'grid' || value.viewMode === 'list'
        const validDensity = value.density === 'compact' || value.density === 'comfortable' || value.density === 'large'
        return validMode && validDensity ? [[key, { viewMode: value.viewMode!, density: value.density! }]] : []
      }))
    } catch {
      return {}
    }
  }
  const videoViewPreferences = reactive<Record<string, VideoViewPreference>>(readVideoViewPreferences())

  const toggleSidebar = (options?: SidebarStateOptions) => {
    isSidebarOpen.value = !isSidebarOpen.value
    if (options?.persist !== false && typeof localStorage !== 'undefined') {
      localStorage.setItem(SIDEBAR_OPEN_KEY, String(isSidebarOpen.value))
    }
  }

  const setSidebarOpen = (open: boolean, options?: SidebarStateOptions) => {
    isSidebarOpen.value = open
    const persist = options?.persist !== false
    if (persist && typeof localStorage !== 'undefined') {
      localStorage.setItem(SIDEBAR_OPEN_KEY, String(open))
    }
  }

  /** Restore the last user-persisted rail preference (route immersion must not poison it). */
  const restorePersistedSidebarOpen = () => {
    isSidebarOpen.value = readPersistedSidebarOpen()
  }

  const getSearchQuery = (scope: string) => searchQueries[scope] ?? ''

  const setSearchQuery = (scope: string, query: string) => {
    searchQueries[scope] = query
  }

  const getSearchTrigger = (scope: string) => searchTriggers[scope] ?? 0

  const triggerSearch = (scope: string, query?: string) => {
    if (query !== undefined) {
      setSearchQuery(scope, query)
    }
    searchTriggers[scope] = getSearchTrigger(scope) + 1
  }

  const setHomeSearchMode = (mode: 'local' | 'remote') => {
    homeSearchMode.value = mode
  }

  const persistVideoViewPreference = (key: string) => {
    if (!key || typeof localStorage === 'undefined') return
    videoViewPreferences[key] = { viewMode: viewMode.value, density: videoDensity.value }
    localStorage.setItem(VIDEO_VIEW_PREFERENCES_KEY, JSON.stringify(videoViewPreferences))
  }

  const applyVideoViewPreference = (key: string) => {
    const preference = videoViewPreferences[key]
    if (!preference) return
    viewMode.value = preference.viewMode
    videoDensity.value = preference.density
  }

  const setViewMode = (mode: VideoViewMode, preferenceKey?: string) => {
    viewMode.value = mode
    if (typeof localStorage !== 'undefined') localStorage.setItem(VIEW_MODE_KEY, mode)
    if (preferenceKey) persistVideoViewPreference(preferenceKey)
  }

  const setVideoDensity = (density: VideoDensity, preferenceKey?: string) => {
    videoDensity.value = density
    if (typeof localStorage !== 'undefined') localStorage.setItem(VIDEO_DENSITY_KEY, density)
    if (preferenceKey) persistVideoViewPreference(preferenceKey)
  }

  const setVideoWidescreen = (enabled: boolean) => {
    isVideoWidescreen.value = enabled
    if (enabled) {
      isVideoSidebarOpen.value = false
    } else {
      isVideoSidebarOpen.value = true
    }
  }

  return {
    isSidebarOpen,
    isVideoWidescreen,
    isVideoSidebarOpen,
    homeSearchMode,
    viewMode,
    videoDensity,
    toggleSidebar,
    setSidebarOpen,
    restorePersistedSidebarOpen,
    getSearchQuery,
    setSearchQuery,
    getSearchTrigger,
    triggerSearch,
    setHomeSearchMode,
    setViewMode,
    setVideoDensity,
    applyVideoViewPreference,
    setVideoWidescreen
  }
})
