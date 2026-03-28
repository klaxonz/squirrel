<template>
  <div class="auth-shell">
    <div class="auth-divider-line"></div>

    <div class="auth-layout">
      <!-- 左侧：品牌展示区 -->
      <aside class="auth-sidebar">
        <div class="auth-sidebar__status">System Ready</div>
        <h1 class="auth-sidebar__brand">SQRL</h1>
        <div class="auth-sidebar__status" style="margin-top: auto; opacity: 0.1">00:00:00 // CINEMA</div>
      </aside>

      <!-- 右侧：交互表单区 -->
      <main class="auth-main">
        <form class="auth-form-minimal" @submit.prevent="handleSubmit">
          <Alert v-if="errorMessage" variant="destructive" class="auth-error-minimal mb-8">
            <AlertDescription>{{ errorMessage }}</AlertDescription>
          </Alert>

          <div class="auth-field-minimal">
            <span class="auth-field-index">01</span>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              placeholder=" "
              class="auth-input-minimal"
            />
            <label for="email" class="auth-label-floating">Identity / Email</label>
          </div>

          <div class="auth-field-minimal">
            <span class="auth-field-index">02</span>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              placeholder=" "
              class="auth-input-minimal"
            />
            <label for="password" class="auth-label-floating">Access / Key</label>
          </div>

          <Button type="submit" class="auth-submit-minimal" :disabled="loading">
            {{ loading ? 'Authenticating...' : 'Enter System' }}
          </Button>

          <div class="auth-footer-minimal">
            <span>Unauthorized?</span>
            <router-link to="/register" class="auth-link-minimal">Request Access</router-link>
          </div>
        </form>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '../composables/useUser'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

const router = useRouter()
const { login } = useUser()
const loading = ref(false)
const errorMessage = ref('')
const form = ref({
  email: '',
  password: '',
})

const getErrorMessage = (error) => {
  if (!error) return '登录失败，请稍后再试。'
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string') return error.message
  if (typeof error?.detail === 'string') return error.detail
  if (typeof error?.response?.data?.detail === 'string') return error.response.data.detail
  return '登录失败，请检查邮箱和密码后重试。'
}

const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const result = await login(form.value)
    if (result.error) {
      errorMessage.value = getErrorMessage(result.error)
      return
    }

    await router.push('/')
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="../styles/views/auth-entry.css"></style>
