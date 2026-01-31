import { ref } from 'vue'
import { getUserMeConfig, updateUserMeConfig } from '@/api'

type UserSettings = {
  showNsfw: boolean
  autoplay: boolean
  autoplayNext: boolean
  loop: boolean
  [key: string]: unknown
}

type ApiResult<T> = { data?: T | null; error?: unknown | null }

const settingsState = ref<UserSettings>({
  showNsfw: false,
  autoplay: true,
  autoplayNext: true,
  loop: false,
})

const loadingState = ref(false)
const errorState = ref<unknown | null>(null)

export function useUserSettings() {
  const loadUserSettings = async () => {
    loadingState.value = true
    errorState.value = null

    const { data, error } = (await getUserMeConfig()) as ApiResult<UserSettings>
    if (!error && data) {
      settingsState.value = {
        ...settingsState.value,
        ...data,
      }
    }

    errorState.value = error
    loadingState.value = false
  }

  const saveUserSettings = async () => {
    loadingState.value = true
    errorState.value = null

    const result = (await updateUserMeConfig({
      settings: settingsState.value,
      merge: false,
    })) as ApiResult<UserSettings>

    if (result.error) {
      errorState.value = result.error

      const rollbackResult = (await getUserMeConfig()) as ApiResult<UserSettings>
      if (!rollbackResult.error && rollbackResult.data) {
        settingsState.value = {
          ...settingsState.value,
          ...rollbackResult.data,
        }
      }

      loadingState.value = false
      return result
    }

    if (result.data) {
      settingsState.value = result.data
    }

    loadingState.value = false
    return result
  }

  return {
    settings: settingsState,
    loading: loadingState,
    error: errorState,
    loadUserSettings,
    saveUserSettings,
  }
}
