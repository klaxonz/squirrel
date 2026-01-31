import { ref } from 'vue'
import { get, post } from '../utils/request'

// 全局共享的系统配置状态
const config = ref(null)
const loading = ref(false)

export function useSystemConfig() {
  const loadSystemConfig = async () => {
    loading.value = true
    try {
      const result = await get('/api/system/config')
      if (!result.error) {
        config.value = result.data
      }
      return result
    } finally {
      loading.value = false
    }
  }

  const updateSystemConfig = async (payload = {}) => {
    loading.value = true
    try {
      const result = await post('/api/system/config', payload)
      if (!result.error) {
        config.value = result.data
      }
      return result
    } finally {
      loading.value = false
    }
  }

  return {
    config,
    loading,
    loadSystemConfig,
    updateSystemConfig,
  }
}
