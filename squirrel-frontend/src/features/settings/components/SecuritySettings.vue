<template>
  <section class="space-y-4">
    <div class="settings-section-title">
      <h3>账户安全</h3>
      <p>修改密码并管理当前账户的登录会话。</p>
    </div>

    <div v-if="securityError" class="settings-alert settings-alert--error">
      <AppIcon name="warning" class="h-4 w-4" />
      {{ securityError }}
    </div>
    <div v-if="securitySuccess" class="settings-alert settings-alert--success">
      <AppIcon name="statusSuccess" class="h-4 w-4" />
      {{ securitySuccess }}
    </div>

    <div class="settings-panel p-4">
      <div class="mb-4 flex items-center gap-2 text-sm font-semibold">
        <AppIcon name="securityAlert" class="h-4 w-4 text-muted-foreground" />
        修改登录密码
      </div>
      <form @submit.prevent="handlePasswordUpdate" class="max-w-md space-y-4">
        <div v-for="field in passwordFields" :key="field.key" class="space-y-2">
          <label class="text-xs font-medium text-muted-foreground">{{ field.label }}</label>
          <Input
            v-model="securityForm[field.key]"
            :type="field.type"
            :placeholder="field.placeholder"
            :disabled="passwordSubmitting"
            class="h-9 rounded-md border-border/50 text-sm shadow-none"
          />
        </div>
        <Button type="submit" :disabled="passwordSubmitting" class="h-9 rounded-md px-3">
          <AppIcon v-if="passwordSubmitting" name="refresh" class="h-4 w-4 animate-spin" />
          {{ passwordSubmitting ? '更新中' : '更新密码' }}
        </Button>
      </form>
    </div>

    <div class="settings-panel">
      <div class="settings-row">
        <div class="min-w-0">
          <div class="settings-row-title">注销其他会话</div>
          <div class="settings-row-desc">使除当前设备外所有已登录的设备失效。</div>
        </div>
        <Button variant="destructive" class="h-9 rounded-md px-3" :disabled="sessionSubmitting" @click="handleRevokeSessions">
          <AppIcon name="logout" class="h-4 w-4" />
          撤销会话
        </Button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { revokeUserSessions, updateUserPassword } from '@/shared/api'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

// ponytail: the security tab owns all of its state and talks to its own two
// API endpoints directly; it has zero cross-tab dependencies, so it needs no
// props or emits. Extracted verbatim from Settings.vue's security section.
const passwordFields = [
  { key: 'currentPassword', label: '当前密码', placeholder: '输入旧密码', type: 'password' },
  { key: 'newPassword', label: '新密码', placeholder: '至少 8 位字符', type: 'password' },
  { key: 'confirmPassword', label: '确认新密码', placeholder: '再次输入新密码', type: 'password' },
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
