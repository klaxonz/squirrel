import { ref } from 'vue'
import { getSystemConfig, saveSystemConfig } from '@/api'
import type { ApiResult } from '@/types/api'

type SystemConfig = Record<string, unknown>

const config = ref<SystemConfig | null>(null)
const loading = ref(false)

export function useSystemConfig() {
  const loadSystemConfig = async () => {
    loading.value = true
    try {
      const result = (await getSystemConfig()) as ApiResult<SystemConfig>
      if (!result.error) {
        config.value = result.data || null
      }
      return result
    } finally {
      loading.value = false
    }
  }

  const updateSystemConfig = async (payload: Record<string, unknown> = {}) => {
    loading.value = true
    try {
      const result = (await saveSystemConfig(payload)) as ApiResult<SystemConfig>
      if (!result.error) {
        config.value = result.data || null
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
