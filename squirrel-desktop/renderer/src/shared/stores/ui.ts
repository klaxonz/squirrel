import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'

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
  const readPersistedViewMode = (): 'grid' | 'list' => {
    if (typeof localStorage === 'undefined') return 'grid'
    return localStorage.getItem(VIEW_MODE_KEY) === 'list' ? 'list' : 'grid'
  }
  const viewMode = ref<'grid' | 'list'>(readPersistedViewMode())

  const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SIDEBAR_OPEN_KEY, String(isSidebarOpen.value))
    }
  }

  const setSidebarOpen = (open: boolean) => {
    isSidebarOpen.value = open
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SIDEBAR_OPEN_KEY, String(open))
    }
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

  const setViewMode = (mode: 'grid' | 'list') => {
    viewMode.value = mode
    if (typeof localStorage !== 'undefined') localStorage.setItem(VIEW_MODE_KEY, mode)
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
    toggleSidebar,
    setSidebarOpen,
    getSearchQuery,
    setSearchQuery,
    getSearchTrigger,
    triggerSearch,
    setHomeSearchMode,
    setViewMode,
    setVideoWidescreen
  }
})
