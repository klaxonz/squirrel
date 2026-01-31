import { ref } from 'vue';
import { get, put } from '../utils/request'

const settingsState = ref({
  showNsfw: false,
  autoplay: true,
  autoplayNext: true,
  loop: false,
});

const loadingState = ref(false);
const errorState = ref(null);

export function useUserSettings() {
  const loadUserSettings = async () => {
    loadingState.value = true;
    errorState.value = null;

    const { data, error } = await get('/api/users/me/config')
    if (!error && data) {
      settingsState.value = {
        ...settingsState.value,
        ...data,
      }
    }

    errorState.value = error
    loadingState.value = false
  };

  const saveUserSettings = async () => {
    loadingState.value = true;
    errorState.value = null;

    const result = await put('/api/users/me/config', {
      settings: settingsState.value,
      merge: false,
    })

    if (result.error) {
      errorState.value = result.error

      const rollbackResult = await get('/api/users/me/config')
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
  };

  return {
    settings: settingsState,
    loading: loadingState,
    error: errorState,
    loadUserSettings,
    saveUserSettings,
  };
}
