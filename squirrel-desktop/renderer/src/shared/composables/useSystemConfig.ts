import { ref } from 'vue'
import { getSystemConfig, saveSystemConfig } from '@/shared/api'

type SystemConfig = Record<string, unknown>

const config = ref<SystemConfig | null>(null)
const loading = ref(false)

export function useSystemConfig() {
  const loadSystemConfig = async () => {
    loading.value = true
    try {
      const data = await getSystemConfig()
      config.value = data || null
      return data
    } finally {
      loading.value = false
    }
  }

  const updateSystemConfig = async (payload: Record<string, unknown> = {}) => {
    loading.value = true
    try {
      const data = await saveSystemConfig(payload)
      config.value = data || null
      return data
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
