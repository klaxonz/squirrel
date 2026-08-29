<template>
  <div class="security-settings">
    <Alert v-if="securityError" variant="error">
      <AppIcon name="warning" class="h-4 w-4" />
      <p class="text-sm [&_p]:leading-relaxed">{{ securityError }}</p>
    </Alert>
    <Alert v-if="securitySuccess" variant="success">
      <AppIcon name="statusSuccess" class="h-4 w-4" />
      <p class="text-sm [&_p]:leading-relaxed">{{ securitySuccess }}</p>
    </Alert>

    <section class="app-settings-section">
      <div class="app-settings-section-title">
        <h2>登录密码</h2>
        <p>更新本账号密码；提交后需用新密码登录其他设备。</p>
      </div>

      <form class="app-settings-panel security-password-form" novalidate @submit.prevent="handlePasswordUpdate">
        <div class="security-password-grid">
          <AppFormField
            v-for="field in passwordFields"
            :id="`security-${field.key}`"
            :key="field.key"
            :label="field.label"
            :description="field.description"
            :error="fieldErrors[field.key]"
            required
            :class="{ 'security-field--full': field.key === 'currentPassword' }"
          >
            <template #default="{ id, control }">
              <div class="security-password-control">
                <Input
                  v-bind="control"
                  :id="id"
                  v-model="securityForm[field.key]"
                  fluid
                  :type="passwordVisible[field.key] ? 'text' : 'password'"
                  :placeholder="field.placeholder"
                  :disabled="passwordSubmitting"
                  :autocomplete="field.autocomplete"
                  :minlength="field.key === 'currentPassword' ? undefined : 8"
                  @input="clearFieldError(field.key)"
                />
                <Button
                  type="button"
                  text
                  variant="secondary"
                  size="sm"
                  icon-only
                  class="security-password-toggle"
                  :aria-label="passwordVisible[field.key] ? `隐藏${field.label}` : `显示${field.label}`"
                  :aria-pressed="passwordVisible[field.key]"
                  @click="passwordVisible[field.key] = !passwordVisible[field.key]"
                >
                  <AppIcon :name="passwordVisible[field.key] ? 'eyeOff' : 'eye'" class="size-4" />
                </Button>
              </div>
            </template>
          </AppFormField>
        </div>
        <div class="security-form-actions">
          <p>新密码至少 8 位，并需与确认密码完全一致。</p>
          <Button type="submit" :loading="passwordSubmitting">
            更新密码
          </Button>
        </div>
      </form>
    </section>

    <section class="app-settings-section">
      <div class="app-settings-section-title">
        <h2>登录会话</h2>
        <p>管理其它设备上的有效会话，当前设备不会被踢出。</p>
      </div>

      <div class="app-settings-panel security-session-panel">
        <div class="app-settings-row security-session-row">
          <div class="app-settings-row__copy">
            <div class="app-settings-row__title">其他设备</div>
            <div class="app-settings-row__desc">撤销所有其他设备的登录状态；当前设备保持登录。</div>
          </div>
          <Button
            variant="secondary"
            outlined
            class="security-revoke-button"
            :loading="sessionSubmitting"
            @click="showRevokeDialog = true"
          >
            <AppIcon name="logout" class="h-4 w-4" />
            注销其他设备
          </Button>
        </div>
      </div>
    </section>

    <ConfirmDialog
      v-model:open="showRevokeDialog"
      icon="logout"
      icon-bg-class="bg-destructive/10 text-destructive"
      title="注销其他设备？"
      description="其他设备上的登录会话将立即失效，正在进行的操作可能会中断；当前设备不会退出。"
      cancel-label="取消"
      confirm-label="确认注销"
      confirm-variant="destructive"
      @confirm="handleRevokeSessions"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { revokeUserSessions, updateUserPassword } from '@/shared/api'
import AppIcon from '@/shared/icons/AppIcon.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import AppFormField from '@/shared/components/layout/AppFormField.vue'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

const passwordFields = [
  {
    key: 'currentPassword',
    label: '当前密码',
    placeholder: '输入旧密码',
    description: '用于确认是你本人在修改密码。',
    autocomplete: 'current-password',
  },
  {
    key: 'newPassword',
    label: '新密码',
    placeholder: '至少 8 位字符',
    description: '至少 8 位字符。',
    autocomplete: 'new-password',
  },
  {
    key: 'confirmPassword',
    label: '确认新密码',
    placeholder: '再次输入新密码',
    description: '必须与新密码一致。',
    autocomplete: 'new-password',
  },
] as const

type PasswordFieldKey = typeof passwordFields[number]['key']

type SecurityForm = Record<PasswordFieldKey, string>
type FieldState<T> = Record<PasswordFieldKey, T>

const securityForm = ref<SecurityForm>({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const passwordVisible = ref<FieldState<boolean>>({
  currentPassword: false,
  newPassword: false,
  confirmPassword: false,
})
const fieldErrors = ref<FieldState<string>>({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const passwordSubmitting = ref(false)
const sessionSubmitting = ref(false)
const showRevokeDialog = ref(false)
const securityError = ref('')
const securitySuccess = ref('')

const resetSecurityFeedback = () => {
  securityError.value = ''
  securitySuccess.value = ''
}

const clearFieldError = (key: PasswordFieldKey) => {
  fieldErrors.value[key] = ''
  resetSecurityFeedback()
}

const validatePasswordForm = () => {
  fieldErrors.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
  let valid = true

  for (const field of passwordFields) {
    if (!securityForm.value[field.key]) {
      fieldErrors.value[field.key] = `请输入${field.label}`
      valid = false
    }
  }
  if (securityForm.value.newPassword && securityForm.value.newPassword.length < 8) {
    fieldErrors.value.newPassword = '新密码至少 8 位'
    valid = false
  }
  if (securityForm.value.confirmPassword && securityForm.value.newPassword !== securityForm.value.confirmPassword) {
    fieldErrors.value.confirmPassword = '两次输入的新密码不一致'
    valid = false
  }
  return valid
}

const handlePasswordUpdate = async () => {
  resetSecurityFeedback()
  if (!validatePasswordForm()) return

  passwordSubmitting.value = true
  try {
    await updateUserPassword({
      current_password: securityForm.value.currentPassword,
      new_password: securityForm.value.newPassword,
    })
    securitySuccess.value = '密码更新成功'
    securityForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
    passwordVisible.value = { currentPassword: false, newPassword: false, confirmPassword: false }
  } catch (err) {
    securityError.value = errorMessage(err, '更新失败')
  } finally {
    passwordSubmitting.value = false
  }
}

const handleRevokeSessions = async () => {
  showRevokeDialog.value = false
  resetSecurityFeedback()
  sessionSubmitting.value = true
  try {
    await revokeUserSessions()
    securitySuccess.value = '其他设备已注销'
  } catch (err) {
    securityError.value = errorMessage(err, '注销其他设备失败')
  } finally {
    sessionSubmitting.value = false
  }
}
</script>

<style scoped>
.security-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.security-password-form {
  max-width: 40rem;
  padding: var(--space-4);
}

.security-session-panel {
  width: 100%;
  max-width: 40rem;
}

.security-session-row {
  min-height: 4rem;
}

.security-password-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.security-field--full {
  grid-column: 1 / -1;
}

.security-password-control {
  position: relative;
}

.security-password-control :deep(input) {
  padding-right: 2.5rem;
}

.security-password-toggle {
  position: absolute;
  top: 50%;
  right: 0.25rem;
  transform: translateY(-50%);
}

.security-form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-top: 1px solid var(--app-surface-border-subtle);
  margin: var(--space-4) calc(var(--space-4) * -1) calc(var(--space-4) * -1);
  padding: var(--space-4);
}

.security-form-actions p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.4;
}

.security-revoke-button {
  min-width: 7.5rem;
  color: hsl(var(--destructive));
}

@media (max-width: 900px) {
  .security-password-grid {
    grid-template-columns: 1fr;
  }

  .security-field--full {
    grid-column: auto;
  }

  .security-form-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
