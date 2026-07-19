import { computed, onScopeDispose, ref, watch } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { usePointerOutside } from '@/shared/composables/usePointerOutside'
import {
  createRssAccount,
  deleteRssAccount,
  getRssAccounts,
  testRssAccount,
  testRssAccountConfig,
  updateRssAccount,
  type RssAccountPayload,
} from '@/shared/api'
import { isApiError } from '@/shared/lib/apiError'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { RssAccount, RssAccountForm } from '@/features/rss/types/rss'

const providers: { value: 'greader' | 'miniflux' | 'fever'; name: string; desc: string; icon: AppIconName }[] = [
  { value: 'greader', name: 'Google Reader', desc: 'Reader API', icon: 'rss' },
  { value: 'miniflux', name: 'Miniflux', desc: 'RSS Service', icon: 'siteFallback' },
  { value: 'fever', name: 'Fever', desc: 'Fever API', icon: 'rss' },
]

export const DEFAULT_RSS_SYNC_ENTRY_LIMIT = 100
export const MAX_RSS_SYNC_ENTRY_LIMIT = 5000

export function useRssAccounts(options?: {
  onRefresh?: () => Promise<void>
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const accounts = ref<RssAccount[]>([])
  const accountsError = ref('')
  const loadingAccounts = ref(false)
  const selectedAccountId = ref<number | null>(null)
  const showAddEditModal = ref(false)
  const showDeleteConfirmModal = ref(false)
  const accountToDelete = ref<RssAccount | null>(null)
  const showAccountDropdown = ref(false)
  const accountDropdownRef = ref<HTMLElement | null>(null)
  const saving = ref(false)
  const testing = ref(false)
  const deleting = ref(false)

  const accountForm = ref<RssAccountForm>({
    id: null as number | null,
    provider: 'greader',
    name: '',
    base_url: '',
    username: '',
    credential: '',
    enabled: true,
    sync_entry_limit: null,
  })
  const originalConnection = ref<Pick<RssAccountForm, 'provider' | 'base_url' | 'username'> | null>(null)
  const formMessage = ref('')
  const formError = ref(false)
  let accountsRequestToken = 0

  const selectedAccount = computed(() => accounts.value.find((a) => a.id === selectedAccountId.value) || null)

  const defaultAccountName = computed(() => {
    const baseUrl = accountForm.value.base_url.trim()
    if (baseUrl) {
      try { return new URL(baseUrl).host }
      catch { return baseUrl }
    }
    return accountForm.value.provider
  })

  const baseUrlPlaceholder = computed(() => {
    if (accountForm.value.provider === 'greader') return 'https://reader.example.com/api/greader.php'
    return 'https://reader.example.com'
  })

  const credentialPlaceholder = computed(() => {
    if (accountForm.value.provider === 'miniflux') return 'API Token'
    return 'API 密码或 Token'
  })

  const requiresUsername = computed(() => {
    return accountForm.value.provider === 'greader' || accountForm.value.provider === 'fever'
  })

  const hasConnectionOverrides = computed(() => {
    const original = originalConnection.value
    if (!original) return true
    return original.provider !== accountForm.value.provider
      || original.base_url !== accountForm.value.base_url.trim()
      || original.username !== accountForm.value.username.trim()
  })

  const canSaveForm = computed(() => {
    const hasRequiredUsername = !requiresUsername.value || !!accountForm.value.username.trim()
    const canReuseStoredCredential = !!accountForm.value.id && !hasConnectionOverrides.value
    const hasRequiredCredential = !!accountForm.value.credential.trim() || canReuseStoredCredential
    const syncEntryLimit = accountForm.value.sync_entry_limit
    const hasValidSyncLimit = accountForm.value.provider === 'greader' || (
      Number.isInteger(syncEntryLimit)
      && Number(syncEntryLimit) >= 1
      && Number(syncEntryLimit) <= MAX_RSS_SYNC_ENTRY_LIMIT
    )
    return !!accountForm.value.base_url.trim() && hasRequiredUsername && hasRequiredCredential && hasValidSyncLimit
  })

  const canTestForm = computed(() => {
    const hasRequiredUsername = !requiresUsername.value || !!accountForm.value.username.trim()
    const canReuseStoredCredential = !!accountForm.value.id && !hasConnectionOverrides.value
    return !!accountForm.value.base_url.trim()
      && hasRequiredUsername
      && (!!accountForm.value.credential.trim() || canReuseStoredCredential)
  })

  watch(() => accountForm.value.provider, (provider) => {
    if (provider === 'greader') {
      accountForm.value.sync_entry_limit = null
      return
    }
    const limit = Number(accountForm.value.sync_entry_limit)
    if (!Number.isInteger(limit) || limit < 1 || limit > MAX_RSS_SYNC_ENTRY_LIMIT) {
      accountForm.value.sync_entry_limit = DEFAULT_RSS_SYNC_ENTRY_LIMIT
    }
  })

  usePointerOutside(accountDropdownRef, () => {
    showAccountDropdown.value = false
  })

  const resetForm = () => {
    accountForm.value = {
      id: null,
      provider: 'greader',
      name: '',
      base_url: '',
      username: '',
      credential: '',
      enabled: true,
      sync_entry_limit: null,
    }
    originalConnection.value = null
    formMessage.value = ''
    formError.value = false
  }

  const openAddAccount = () => {
    resetForm()
    showAddEditModal.value = true
  }

  const openEditAccount = (account: RssAccount) => {
    accountForm.value = {
      id: account.id,
      provider: account.provider,
      name: account.name,
      base_url: account.base_url,
      username: account.username || '',
      credential: '',
      enabled: account.enabled,
      sync_entry_limit: account.sync_entry_limit,
    }
    originalConnection.value = {
      provider: account.provider,
      base_url: account.base_url,
      username: account.username || '',
    }
    formMessage.value = ''
    formError.value = false
    showAddEditModal.value = true
  }

  const confirmDeleteAccount = (account: RssAccount) => {
    accountToDelete.value = account
    showDeleteConfirmModal.value = true
  }

  const loadAccounts = async () => {
    const requestToken = ++accountsRequestToken
    loadingAccounts.value = true
    accountsError.value = ''
    try {
      const data = await getRssAccounts()
      if (requestToken !== accountsRequestToken) return

      accounts.value = data?.data || []
      if (!accounts.value.some((account) => account.id === selectedAccountId.value)) {
        selectedAccountId.value = accounts.value[0]?.id ?? null
      }
    } catch (err) {
      if (requestToken !== accountsRequestToken) return

      accountsError.value = errorMessage(err, '加载账号失败')
      options?.onStatus?.(accountsError.value, true)
    } finally {
      if (requestToken === accountsRequestToken) {
        loadingAccounts.value = false
      }
    }
  }

  onScopeDispose(() => {
    accountsRequestToken += 1
  })

  const saveAccount = async () => {
    saving.value = true
    formMessage.value = ''
    const payload: RssAccountPayload = {
      provider: accountForm.value.provider,
      name: accountForm.value.name.trim() || defaultAccountName.value,
      base_url: accountForm.value.base_url.trim(),
      username: accountForm.value.username.trim() || undefined,
      enabled: accountForm.value.enabled,
      sync_entry_limit: accountForm.value.sync_entry_limit,
    }
    if (accountForm.value.credential.trim()) {
      payload.credential = accountForm.value.credential
    }
    try {
      let savedAccount: RssAccount
      if (accountForm.value.id) {
        savedAccount = await updateRssAccount(accountForm.value.id, payload)
      } else {
        savedAccount = await createRssAccount(payload)
      }
      selectedAccountId.value = savedAccount.id
      formError.value = false
      formMessage.value = '已保存'
      showAddEditModal.value = false
      resetForm()
      await options?.onRefresh?.()
    } catch (err) {
      formError.value = true
      formMessage.value = errorMessage(err, '保存失败')
    } finally {
      saving.value = false
    }
  }

  const testForm = async () => {
    testing.value = true
    formMessage.value = ''
    try {
      const canUseSavedConfig = !!accountForm.value.id
        && !accountForm.value.credential.trim()
        && !hasConnectionOverrides.value
      const data = canUseSavedConfig
        ? await testRssAccount(accountForm.value.id!)
        : await testRssAccountConfig({
            provider: accountForm.value.provider,
            base_url: accountForm.value.base_url.trim(),
            username: accountForm.value.username.trim() || undefined,
            credential: accountForm.value.credential,
          })
      formError.value = false
      formMessage.value = `连接成功，发现 ${(data as { feed_count?: number } | null)?.feed_count ?? 0} 个 Feed`
    } catch (err) {
      formError.value = true
      formMessage.value = isApiError(err) ? err.message : '连接失败'
    } finally {
      testing.value = false
    }
  }

  const handleDeleteAccount = async () => {
    if (!accountToDelete.value || deleting.value) return
    deleting.value = true
    try {
      await deleteRssAccount(accountToDelete.value.id)
      options?.onStatus?.(`已成功删除账号「${accountToDelete.value.name}」`)
      showDeleteConfirmModal.value = false
      if (selectedAccountId.value === accountToDelete.value.id) {
        selectedAccountId.value = null
      }
      accountToDelete.value = null
      await options?.onRefresh?.()
    } catch (err) {
      options?.onStatus?.(errorMessage(err, '删除失败'), true)
      showDeleteConfirmModal.value = false
    } finally {
      deleting.value = false
    }
  }

  return {
    providers,
    accounts,
    accountsError,
    loadingAccounts,
    selectedAccountId,
    showAddEditModal,
    showDeleteConfirmModal,
    accountToDelete,
    showAccountDropdown,
    accountDropdownRef,
    saving,
    testing,
    deleting,
    accountForm,
    formMessage,
    formError,
    selectedAccount,
    defaultAccountName,
    baseUrlPlaceholder,
    credentialPlaceholder,
    requiresUsername,
    canSaveForm,
    canTestForm,
    resetForm,
    openAddAccount,
    openEditAccount,
    confirmDeleteAccount,
    loadAccounts,
    saveAccount,
    testForm,
    handleDeleteAccount,
  }
}
