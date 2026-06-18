import { computed, ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import {
  createRssAccount,
  deleteRssAccount,
  getRssAccounts,
  testRssAccountConfig,
  updateRssAccount,
  type RssAccountPayload,
} from '@/api'
import type { AppIconName } from '@/icons/app-icons'
import type { ApiResult, RssAccount } from './rssTypes'

const providers: { value: 'greader' | 'miniflux' | 'fever'; name: string; desc: string; icon: AppIconName }[] = [
  { value: 'greader', name: 'Google Reader', desc: 'Reader API', icon: 'rss' },
  { value: 'miniflux', name: 'Miniflux', desc: 'RSS Service', icon: 'siteFallback' },
  { value: 'fever', name: 'Fever', desc: 'Fever API', icon: 'brand' },
]

export function useRssAccounts(options?: {
  onRefresh?: () => Promise<void>
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const accounts = ref<RssAccount[]>([])
  const selectedAccountId = ref<number | null>(null)
  const showAddEditModal = ref(false)
  const showDeleteConfirmModal = ref(false)
  const accountToDelete = ref<RssAccount | null>(null)
  const showAccountDropdown = ref(false)
  const accountDropdownRef = ref<HTMLElement | null>(null)
  const saving = ref(false)
  const testing = ref(false)

  const accountForm = ref({
    id: null as number | null,
    provider: 'greader',
    name: '',
    base_url: '',
    username: '',
    credential: '',
    enabled: true,
  })
  const formMessage = ref('')
  const formError = ref(false)

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

  const canSaveForm = computed(() => {
    return !!accountForm.value.base_url.trim() && (!!accountForm.value.id || !!accountForm.value.credential.trim())
  })

  const canTestForm = computed(() => {
    return !!accountForm.value.base_url.trim() && !!accountForm.value.credential.trim()
  })

  onClickOutside(accountDropdownRef, () => {
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
    }
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
    const response = await getRssAccounts() as ApiResult<{ data: RssAccount[] }>
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '加载 RSS 账号失败', true)
      return
    }
    accounts.value = response.data?.data || []
    if (!selectedAccountId.value && accounts.value.length) {
      selectedAccountId.value = accounts.value[0].id
    }
  }

  const saveAccount = async () => {
    saving.value = true
    formMessage.value = ''
    const payload: RssAccountPayload = {
      provider: accountForm.value.provider,
      name: accountForm.value.name.trim() || defaultAccountName.value,
      base_url: accountForm.value.base_url,
      username: accountForm.value.username,
      enabled: accountForm.value.enabled,
    }
    if (accountForm.value.credential.trim()) {
      payload.credential = accountForm.value.credential
    }
    const accountId = accountForm.value.id
      ? await updateRssAccount(accountForm.value.id, payload)
      : await createRssAccount(payload)
    saving.value = false
    if (accountId.error) {
      formError.value = true
      formMessage.value = (accountId.error as { message?: string })?.message || '保存失败'
      return
    }
    formError.value = false
    formMessage.value = '已保存'
    showAddEditModal.value = false
    resetForm()
    await options?.onRefresh?.()
  }

  const testForm = async () => {
    testing.value = true
    formMessage.value = ''
    const response = await testRssAccountConfig({
      provider: accountForm.value.provider,
      name: accountForm.value.name || accountForm.value.provider,
      base_url: accountForm.value.base_url,
      username: accountForm.value.username,
      credential: accountForm.value.credential,
    })
    testing.value = false
    formError.value = !!response.error
    formMessage.value = response.error ? (response.error as { message?: string })?.message || '连接失败' : `连接成功，发现 ${(response.data as { feed_count?: number } | null)?.feed_count ?? 0} 个 Feed`
  }

  const handleDeleteAccount = async () => {
    if (!accountToDelete.value) return
    const response = await deleteRssAccount(accountToDelete.value.id)
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '删除账号失败', true)
      showDeleteConfirmModal.value = false
      return
    }
    options?.onStatus?.(`已成功删除账号「${accountToDelete.value.name}」`)
    showDeleteConfirmModal.value = false
    if (selectedAccountId.value === accountToDelete.value.id) {
      selectedAccountId.value = null
    }
    accountToDelete.value = null
    await options?.onRefresh?.()
  }

  return {
    providers,
    accounts,
    selectedAccountId,
    showAddEditModal,
    showDeleteConfirmModal,
    accountToDelete,
    showAccountDropdown,
    accountDropdownRef,
    saving,
    testing,
    accountForm,
    formMessage,
    formError,
    selectedAccount,
    defaultAccountName,
    baseUrlPlaceholder,
    credentialPlaceholder,
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
