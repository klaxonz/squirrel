import { ref } from 'vue'
import { getUserMeConfig, updateUserMeConfig } from '@/shared/api'

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

      const { data, error } = await getUserMeConfig()
      if (!error && data) {
        settingsState.value = {
          ...settingsState.value,
          ...data,
        }
      }

      errorState.value = error
      loadedState.value = true
      loadingState.value = false
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

    const response = await updateUserMeConfig({
      settings: settingsState.value,
      merge: false,
    })

    if (response.error) {
      errorState.value = response.error

      const rollbackResult = await getUserMeConfig()
      if (!rollbackResult.error && rollbackResult.data) {
        settingsState.value = {
          ...settingsState.value,
          ...rollbackResult.data,
        }
      }

      loadingState.value = false
      return response
    }

    if (response.data) {
      // ponytail: UserConfig fields are optional server-side; merge onto
      // defaults so the store always carries a complete UserSettings shape.
      settingsState.value = {
        showNsfw: response.data.showNsfw ?? settingsState.value.showNsfw,
        autoplay: response.data.autoplay ?? settingsState.value.autoplay,
        autoplayNext: response.data.autoplayNext ?? settingsState.value.autoplayNext,
        loop: response.data.loop ?? settingsState.value.loop,
      }
    }

    loadingState.value = false
    return response
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
