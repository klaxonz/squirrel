import { ref } from 'vue'
import axios from '../utils/axios'

/**
 * 对齐项目现有 axios 封装与 Settings 页风格：
 * - 统一使用 axios 实例（携带基础 URL/拦截器/鉴权头）
 * - 与 Settings.vue 一样返回 data.data 或按后端 code 判定
 */

const loading = ref(false)

export function useSystemConfig() {
  const config = ref(null)

  const loadSystemConfig = async () => {
    loading.value = true
    try {
      const resp = await axios.get('/api/system/config')
      // 后端为直接返回对象结构，非 { code, data } 包装，直接使用 resp.data
      config.value = resp.data
      return resp.data
    } finally {
      loading.value = false
    }
  }

  const updateSystemConfig = async (payload = {}) => {
    loading.value = true
    try {
      // 统一改为 JSON 提交，配合后端仅支持 JSON Body 的实现
      const resp = await axios.post('/api/system/config', payload, {
        headers: { 'Content-Type': 'application/json' }
      })
      config.value = resp.data
      return resp.data
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