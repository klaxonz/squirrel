import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const isSidebarOpen = ref(true)
  const isSidebarFlyoutOpen = ref(false)
  const isVideoWidescreen = ref(false)
  const isVideoSidebarOpen = ref(true)
  const searchQuery = ref('')
  const searchTrigger = ref(0)

  const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value
  }

  const triggerSearch = (query?: string) => {
    if (query !== undefined) {
      searchQuery.value = query
    }
    searchTrigger.value++
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
    toggleSidebar,
    triggerSearch,
    setVideoWidescreen
  }
})
