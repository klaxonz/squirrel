import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const isSidebarOpen = ref(true)
  const isSidebarFlyoutOpen = ref(false)
  const isVideoWidescreen = ref(false)
  const isVideoSidebarOpen = ref(true)
  const searchQuery = ref('')
  const searchTrigger = ref(0)
  const homeSearchMode = ref<'local' | 'remote'>('local')

  const VIEW_MODE_KEY = 'ui.viewMode'
  const readPersistedViewMode = (): 'grid' | 'list' => {
    if (typeof localStorage === 'undefined') return 'grid'
    return localStorage.getItem(VIEW_MODE_KEY) === 'list' ? 'list' : 'grid'
  }
  const viewMode = ref<'grid' | 'list'>(readPersistedViewMode())

  const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value
  }

  const triggerSearch = (query?: string) => {
    if (query !== undefined) {
      searchQuery.value = query
    }
    searchTrigger.value++
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
      isSidebarFlyoutOpen.value = false
      isVideoSidebarOpen.value = false
    } else {
      isVideoSidebarOpen.value = true
    }
  }

  return {
    isSidebarOpen,
    isSidebarFlyoutOpen,
    isVideoWidescreen,
    isVideoSidebarOpen,
    searchQuery,
    searchTrigger,
    homeSearchMode,
    viewMode,
    toggleSidebar,
    triggerSearch,
    setHomeSearchMode,
    setViewMode,
    setVideoWidescreen
  }
})
