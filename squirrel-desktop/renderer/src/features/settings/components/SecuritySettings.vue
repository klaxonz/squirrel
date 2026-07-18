<template>
  <div class="security-settings">
    <Alert
      v-if="securityError"
      variant="error"
    >
      <AppIcon name="warning" class="h-4 w-4" />
      <AlertDescription>{{ securityError }}</AlertDescription>
    </Alert>
    <Alert
      v-if="securitySuccess"
      variant="success"
    >
      <AppIcon name="statusSuccess" class="h-4 w-4" />
      <AlertDescription>{{ securitySuccess }}</AlertDescription>
    </Alert>

    <section class="app-settings-section">
      <div class="app-settings-section-title">
        <h2>登录密码</h2>
        <p>更新本账号密码；提交后需用新密码登录其他设备。</p>
      </div>

      <form class="app-settings-panel security-password-form" @submit.prevent="handlePasswordUpdate">
        <div class="security-password-grid">
          <div
            v-for="field in passwordFields"
            :key="field.key"
            class="security-field"
            :class="{ 'security-field--full': field.key === 'currentPassword' }"
          >
            <label :for="`security-${field.key}`" class="security-field__label">
              {{ field.label }}
            </label>
            <Input
              :id="`security-${field.key}`"
              v-model="securityForm[field.key]"
              :type="field.type"
              :placeholder="field.placeholder"
              :disabled="passwordSubmitting"
              :autocomplete="field.autocomplete"
            />
          </div>
        </div>
        <div class="security-form-actions">
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

      <div class="app-settings-panel">
        <div class="app-settings-row">
          <div class="app-settings-row__copy">
            <div class="app-settings-row__title">注销其他设备</div>
            <div class="app-settings-row__desc">立即吊销除本机以外的全部会话令牌。</div>
          </div>
          <Button
            variant="outline"
            class="security-revoke-button"
            :loading="sessionSubmitting"
            @click="handleRevokeSessions"
          >
            <AppIcon name="logout" class="h-4 w-4" />
            注销其他设备
          </Button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { revokeUserSessions, updateUserPassword } from '@/shared/api'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Alert, AlertDescription } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

const passwordFields = [
  {
    key: 'currentPassword',
    label: '当前密码',
    placeholder: '输入旧密码',
    type: 'password',
    autocomplete: 'current-password',
  },
  {
    key: 'newPassword',
    label: '新密码',
    placeholder: '至少 8 位字符',
    type: 'password',
    autocomplete: 'new-password',
  },
  {
    key: 'confirmPassword',
    label: '确认新密码',
    placeholder: '再次输入新密码',
    type: 'password',
    autocomplete: 'new-password',
  },
] as const

interface SecurityForm {
  currentPassword: string
  newPassword: string
  confirmPassword: string
  [key: string]: string
}

const securityForm = ref<SecurityForm>({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const passwordSubmitting = ref(false)
const sessionSubmitting = ref(false)
const securityError = ref('')
const securitySuccess = ref('')

const resetSecurityFeedback = () => {
  securityError.value = ''
  securitySuccess.value = ''
}

const handlePasswordUpdate = async () => {
  resetSecurityFeedback()
  if (!securityForm.value.currentPassword || !securityForm.value.newPassword || !securityForm.value.confirmPassword) {
    securityError.value = '请填写完整信息'
    return
  }
  if (securityForm.value.newPassword.length < 8) {
    securityError.value = '新密码至少 8 位'
    return
  }
  if (securityForm.value.newPassword !== securityForm.value.confirmPassword) {
    securityError.value = '两次输入不一致'
    return
  }
  passwordSubmitting.value = true
  try {
    await updateUserPassword({
      current_password: securityForm.value.currentPassword,
      new_password: securityForm.value.newPassword,
    })
    securitySuccess.value = '密码更新成功'
    securityForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
  } catch (err) {
    securityError.value = errorMessage(err, '更新失败')
  } finally {
    passwordSubmitting.value = false
  }
}

const handleRevokeSessions = async () => {
  resetSecurityFeedback()
  sessionSubmitting.value = true
  try {
    await revokeUserSessions()
    securitySuccess.value = '其他会话已撤销'
  } catch {
    securityError.value = '撤销失败'
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

.security-password-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.security-field {
  min-width: 0;
}

.security-field--full {
  grid-column: 1 / -1;
}

.security-field__label {
  display: block;
  margin-bottom: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
}

.security-form-actions {
  display: flex;
  justify-content: flex-start;
  border-top: 1px solid var(--app-surface-border-subtle);
  margin: var(--space-4) calc(var(--space-4) * -1) calc(var(--space-4) * -1);
  padding: var(--space-4);
}

.security-revoke-button {
  color: hsl(var(--destructive));
}

@media (max-width: 900px) {
  .security-password-grid {
    grid-template-columns: 1fr;
  }

  .security-field--full {
    grid-column: auto;
  }
}
</style>
