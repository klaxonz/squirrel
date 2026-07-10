import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import {
  normalizeServerUrl,
  useServerConfig,
} from '@/shared/composables/useServerConfig'
import { useToast } from '@/shared/components/toast/useToast'
import { Logger } from '@/shared/lib/logger'
import { logoutAndRedirect } from '@/shared/lib/auth'

export interface UseServerConfigFormReturn {
  serverForm: Ref<{ url: string }>
  serverSaving: Ref<boolean>
  serverTesting: Ref<boolean>
  serverTestResult: Ref<boolean | null>
  serverTestMessage: Ref<string>
  canSwitchServer: ComputedRef<boolean>
  handleTestServer: () => Promise<void>
  handleSwitchServer: () => Promise<void>
}

export function useServerConfigForm(): UseServerConfigFormReturn {
  const { serverUrl: currentServerUrl, setServerUrl, testServerConnection } = useServerConfig()
  const toast = useToast()

  const serverForm = ref({ url: '' })
  const serverSaving = ref(false)
  const serverTesting = ref(false)
  const serverTestResult = ref<boolean | null>(null)
  const serverTestMessage = ref('')
  const testedServerUrl = ref('')

  const targetServerUrl = computed(() => normalizeServerUrl(serverForm.value.url))
  const canSwitchServer = computed(() => {
    return Boolean(targetServerUrl.value && targetServerUrl.value !== currentServerUrl.value)
  })

  const resetTestResult = () => {
    serverTestResult.value = null
    serverTestMessage.value = ''
    testedServerUrl.value = ''
  }

  watch(
    () => serverForm.value.url,
    () => {
      if (targetServerUrl.value !== testedServerUrl.value) {
        resetTestResult()
      }
    },
  )

  const testTargetServer = async (url: string): Promise<boolean> => {
    try {
      const result = await testServerConnection(url)
      serverTestResult.value = result.ok
      serverTestMessage.value = result.message
      testedServerUrl.value = url
      return result.ok
    } catch (err) {
      Logger.warn('[Settings] Server test failed', err)
      serverTestResult.value = false
      serverTestMessage.value = '无法连接'
      testedServerUrl.value = url
      return false
    }
  }

  const handleTestServer = async () => {
    const url = targetServerUrl.value
    if (!url) {
      serverTestResult.value = false
      serverTestMessage.value = '无效的地址格式'
      return
    }

    serverTesting.value = true
    try {
      await testTargetServer(url)
    } finally {
      serverTesting.value = false
    }
  }

  const handleSwitchServer = async () => {
    const url = targetServerUrl.value
    if (!url) {
      toast.error('无效的服务器地址')
      return
    }
    if (url === currentServerUrl.value) {
      return
    }

    serverSaving.value = true
    try {
      const hasValidTest = testedServerUrl.value === url && serverTestResult.value === true
      if (!hasValidTest && !(await testTargetServer(url))) {
        toast.error(serverTestMessage.value || '无法连接到服务器')
        return
      }

      const ok = await setServerUrl(url)
      if (!ok) {
        toast.error('无效的服务器地址')
        return
      }

      await logoutAndRedirect()
    } catch (err) {
      Logger.warn('[Settings] Failed to switch server', err)
      toast.error('切换服务器失败')
    } finally {
      serverSaving.value = false
    }
  }

  return {
    serverForm,
    serverSaving,
    serverTesting,
    serverTestResult,
    serverTestMessage,
    canSwitchServer,
    handleTestServer,
    handleSwitchServer,
  }
}
