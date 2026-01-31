import { ref } from 'vue'
import { getSystemConfig, saveSystemConfig } from '@/api'

// 全局共享的系统配置状态
const config = ref(null)
const loading = ref(false)

export function useSystemConfig() {
  const loadSystemConfig = async () => {
    loading.value = true
    try {
      const result = await getSystemConfig()
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
      const result = await saveSystemConfig(payload)
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
