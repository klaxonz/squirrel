import { ref } from 'vue'
import { getSystemConfig, saveSystemConfig } from '@/api'

type SystemConfig = Record<string, unknown>

const config = ref<SystemConfig | null>(null)
const loading = ref(false)

export function useSystemConfig() {
  const loadSystemConfig = async () => {
    loading.value = true
    try {
      const response = await getSystemConfig()
      if (!response.error) {
        config.value = response.data || null
      }
      return response
    } finally {
      loading.value = false
    }
  }

  const updateSystemConfig = async (payload: Record<string, unknown> = {}) => {
    loading.value = true
    try {
      const response = await saveSystemConfig(payload)
      if (!response.error) {
        config.value = response.data || null
      }
      return response
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
