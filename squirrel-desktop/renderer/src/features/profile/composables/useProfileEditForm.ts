import { computed, onUnmounted, reactive, ref, type ComputedRef, type Ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import type { useUserStore } from '@/shared/stores/user'

/**
 * Profile-edit form state machine.
 *
 * Owns the nickname/avatar form, the save flow (loading / saved-banner / error),
 * the "saved" banner auto-dismiss timer (cleared on unmount), and the diff-only
 * payload (only changed fields are sent). `hasChanges` gates the save button.
 *
 * The form is hydrated from the store's currentUser on creation; the host calls
 * `hydrate()` itself if it needs to re-sync after mount (it does, to pick up the
 * store value once populated).
 *
 * Extracted from Profile.vue so the save state machine + the diff-payload policy
 * + the banner auto-dismiss timer live in one place rather than inline with the
 * avatar-focus + logout wiring.
 */
interface ProfileForm {
  nickname: string
  avatar: string
}

interface UpdateProfileResult {
  error?: unknown
}

export interface UseProfileEditFormOptions {
  userStore: ReturnType<typeof useUserStore>
}

export interface UseProfileEditFormReturn {
  form: ProfileForm
  saving: Ref<boolean>
  saved: Ref<boolean>
  saveError: Ref<string>
  hasChanges: ComputedRef<boolean>
  hydrate: () => void
  handleSave: () => Promise<void>
}

const SAVED_BANNER_MS = 3000

export function useProfileEditForm(options: UseProfileEditFormOptions): UseProfileEditFormReturn {
  const { userStore } = options

  const form = reactive<ProfileForm>({ nickname: '', avatar: '' })

  const saving = ref(false)
  const saved = ref(false)
  const saveError = ref('')
  let savedTimer: ReturnType<typeof setTimeout> | null = null

  onUnmounted(() => {
    if (savedTimer) clearTimeout(savedTimer)
  })

  const hasChanges = computed(() => {
    if (!userStore.currentUser) return false
    return (
      form.nickname !== (userStore.currentUser.nickname || '')
      || form.avatar !== (userStore.currentUser.avatar || '')
    )
  })

  const hydrate = () => {
    if (userStore.currentUser) {
      form.nickname = userStore.currentUser.nickname || ''
      form.avatar = userStore.currentUser.avatar || ''
    }
  }

  const handleSave = async () => {
    saving.value = true
    saved.value = false
    saveError.value = ''

    // Diff-only payload: only send fields that actually changed.
    const payload: Record<string, string> = {}
    if (form.nickname !== (userStore.currentUser?.nickname || '')) {
      payload.nickname = form.nickname
    }
    if (form.avatar !== (userStore.currentUser?.avatar || '')) {
      payload.avatar = form.avatar
    }

    if (!Object.keys(payload).length) {
      saving.value = false
      return
    }

    const result = (await userStore.updateProfile(payload)) as UpdateProfileResult
    saving.value = false
    if (result.error) {
      saveError.value = errorMessage(result.error, '保存失败')
    } else {
      saved.value = true
      if (savedTimer) clearTimeout(savedTimer)
      savedTimer = setTimeout(() => {
        saved.value = false
      }, SAVED_BANNER_MS)
    }
  }

  return {
    form,
    saving,
    saved,
    saveError,
    hasChanges,
    hydrate,
    handleSave,
  }
}
