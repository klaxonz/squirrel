import { ref } from 'vue';
import axios from '../utils/axios';

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
    try {
      const response = await axios.get('/api/users/me/config');
      if (response.data.code === 0) {
        settingsState.value = {
          ...settingsState.value,
          ...response.data.data,
        };
      } else {
        throw new Error(response.data.msg || '获取用户设置失败');
      }
    } catch (error) {
      console.error('获取用户设置失败:', error);
      errorState.value = error;
    } finally {
      loadingState.value = false;
    }
  };

  const saveUserSettings = async () => {
    loadingState.value = true;
    errorState.value = null;
    try {
      const response = await axios.put('/api/users/me/config', {
        settings: settingsState.value,
        merge: false,
      });
      if (response.data.code === 0) {
        settingsState.value = response.data.data;
      } else {
        throw new Error(response.data.msg || '保存用户设置失败');
      }
    } catch (error) {
      console.error('保存用户设置失败:', error);
      errorState.value = error;
      // 回滚到服务器最新配置
      try {
        const resp = await axios.get('/api/users/me/config');
        if (resp.data.code === 0) {
          settingsState.value = {
            ...settingsState.value,
            ...resp.data.data,
          };
        }
      } catch (e) {
        console.error('回滚用户设置失败:', e);
      }
    } finally {
      loadingState.value = false;
    }
  };

  return {
    settings: settingsState,
    loading: loadingState,
    error: errorState,
    loadUserSettings,
    saveUserSettings,
  };
}
