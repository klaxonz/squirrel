import { ref } from 'vue'
import { getUserMeConfig, updateUserMeConfig } from '@/shared/api'
import { isApiError } from '@/shared/lib/apiError'

type UserSettings = {
  showNsfw: boolean
  autoplay: boolean
  autoplayNext: boolean
  loop: boolean
  [key: string]: unknown
}

const settingsState = ref<UserSettings>({
  showNsfw: false,
  autoplay: true,
  autoplayNext: true,
  loop: false,
})

const loadingState = ref(false)
const errorState = ref<unknown | null>(null)
const loadedState = ref(false)
let loadPromise: Promise<void> | null = null

export function useUserSettings() {
  const loadUserSettings = async (force = false) => {
    if (!force) {
      if (loadedState.value) {
        return
      }
      if (loadPromise) {
        return loadPromise
      }
    }

    loadPromise = (async () => {
      loadingState.value = true
      errorState.value = null

      try {
        const data = await getUserMeConfig()
        if (data) {
          settingsState.value = {
            ...settingsState.value,
            ...data,
          }
        }
        loadedState.value = true
      } catch (error) {
        errorState.value = error
        loadedState.value = true
      } finally {
        loadingState.value = false
      }
    })()

    try {
      await loadPromise
    } finally {
      loadPromise = null
    }
  }

  const saveUserSettings = async () => {
    loadingState.value = true
    errorState.value = null

    try {
      const data = await updateUserMeConfig({
        settings: settingsState.value,
        merge: false,
      })

      if (data) {
        // ponytail: UserConfig fields are optional server-side; merge onto
        // defaults so the store always carries a complete UserSettings shape.
        settingsState.value = {
          showNsfw: data.showNsfw ?? settingsState.value.showNsfw,
          autoplay: data.autoplay ?? settingsState.value.autoplay,
          autoplayNext: data.autoplayNext ?? settingsState.value.autoplayNext,
          loop: data.loop ?? settingsState.value.loop,
        }
      }
      return data
    } catch (error) {
      errorState.value = error
      // Roll back to the server's view so the UI doesn't show unsaved toggles.
      if (isApiError(error)) {
        try {
          const rollback = await getUserMeConfig()
          if (rollback) {
            settingsState.value = { ...settingsState.value, ...rollback }
          }
        } catch {
          // rollback failed — leave the local state; the error is already surfaced
        }
      }
      throw error
    } finally {
      loadingState.value = false
    }
  }

  return {
    settings: settingsState,
    loading: loadingState,
    loaded: loadedState,
    error: errorState,
    loadUserSettings,
    saveUserSettings,
  }
}
