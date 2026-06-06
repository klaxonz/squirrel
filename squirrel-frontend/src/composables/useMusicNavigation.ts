import { ref, computed } from 'vue'

export type MusicView =
  | 'home'
  | 'search'
  | 'fm'
  | 'ranks'
  | 'playlists'
  | 'playlist-detail'
  | 'user-playlist-detail'
  | 'artist-detail'
  | 'album-detail'
  | 'profile'
  | 'new-songs'
  | 'new-albums'
  | 'ai-recommend'
  | 'everyday-recommend'
  | 'favorites'

export function useMusicNavigation() {
  const activeView = ref<MusicView>('home')
  const viewHistory = ref<MusicView[]>([])

  function navigateTo(view: MusicView) {
    if (view !== activeView.value) {
      viewHistory.value.push(activeView.value)
      if (viewHistory.value.length > 20) {
        viewHistory.value.shift()
      }
      activeView.value = view
    }
  }

  function goBack() {
    const previousView = viewHistory.value.pop()
    if (previousView) {
      activeView.value = previousView
      return true
    }
    return false
  }

  function goHome() {
    activeView.value = 'home'
    viewHistory.value = []
  }

  const canGoBack = computed(() => viewHistory.value.length > 0)

  const isDetailView = computed(() =>
    ['playlist-detail', 'user-playlist-detail', 'artist-detail', 'album-detail'].includes(activeView.value)
  )

  return {
    activeView,
    viewHistory,
    navigateTo,
    goBack,
    goHome,
    canGoBack,
    isDetailView,
  }
}
