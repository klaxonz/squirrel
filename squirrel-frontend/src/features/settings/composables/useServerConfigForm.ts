import { ref, type Ref } from 'vue'
import { useServerConfig } from '@/shared/composables/useServerConfig'
import { useToast } from '@/shared/components/toast/useToast'
import { Logger } from '@/shared/lib/logger'

/**
 * Server-URL config form: test-connection + save flow.
 *
 * Owns the form url field, the test/save loading flags, and the test result
 * (ok + message). `handleTestServer` probes the entered URL and surfaces the
 * outcome; `handleSaveServer` persists it via the shared useServerConfig,
 * rejecting empty/invalid urls. The saved url field is re-synced from the
 * shared config after a successful save so it tracks the canonical value.
 *
 * Extracted from Settings.vue so the test→result→save state machine + its
 * loading guards + error mapping live in one place rather than interleaved
 * with theme / user-settings / system-config wiring. The host still owns the
 * initial `initServerConfig()` mount call (it coordinates parallel loads).
 */
export interface UseServerConfigFormReturn {
  serverForm: Ref<{ url: string }>
  serverSaving: Ref<boolean>
  serverTesting: Ref<boolean>
  serverTestResult: Ref<boolean | null>
  serverTestMessage: Ref<string>
  handleTestServer: () => Promise<void>
  handleSaveServer: () => Promise<void>
}

export function useServerConfigForm(): UseServerConfigFormReturn {
  const { serverUrl: currentServerUrl, setServerUrl, testServerConnection } = useServerConfig()
  const toast = useToast()

  const serverForm = ref({ url: '' })
  const serverSaving = ref(false)
  const serverTesting = ref(false)
  const serverTestResult = ref<boolean | null>(null)
  const serverTestMessage = ref('')

  const handleTestServer = async () => {
    if (!serverForm.value.url.trim()) return
    serverTesting.value = true
    serverTestResult.value = null
    try {
      const result = await testServerConnection(serverForm.value.url)
      serverTestResult.value = result.ok
      serverTestMessage.value = result.message
    } catch (err) {
      Logger.warn('[Settings] Server test failed', err)
      serverTestResult.value = false
      serverTestMessage.value = '无法连接'
    } finally {
      serverTesting.value = false
    }
  }

  const handleSaveServer = async () => {
    if (!serverForm.value.url.trim()) return
    serverSaving.value = true
    try {
      const ok = await setServerUrl(serverForm.value.url)
      if (!ok) {
        toast.error('无效的服务器地址')
        return
      }
      toast.success('服务器已更新')
      // Re-sync from the canonical shared value so the field never drifts.
      serverForm.value.url = currentServerUrl.value || ''
    } catch (err) {
      Logger.warn('[Settings] Failed to save server', err)
      toast.error('保存失败')
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
    handleTestServer,
    handleSaveServer,
  }
}
