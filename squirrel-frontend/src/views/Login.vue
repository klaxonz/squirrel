<template>
  <div class="auth-shell">
    <div class="auth-divider-line"></div>

    <div class="auth-layout">
      <!-- 左侧：品牌展示区 -->
      <aside class="auth-sidebar">
        <div class="auth-sidebar__status">系统已就绪</div>
        <h1 class="auth-sidebar__brand">SQRL</h1>
        <div class="auth-sidebar__status" style="margin-top: auto; opacity: 0.1">00:00:00 // 影院系统</div>
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
            <label for="email" class="auth-label-floating">邮箱</label>
          </div>

          <div class="auth-field-minimal">
            <span class="auth-field-index">02</span>
            <input
              id="password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder=" "
              class="auth-input-minimal"
            />
            <label for="password" class="auth-label-floating">密码</label>
            <button
              type="button"
              class="auth-password-toggle"
              @click="showPassword = !showPassword"
            >
              <component :is="showPassword ? EyeOff : Eye" class="w-4 h-4" />
            </button>
          </div>

          <label class="auth-option-minimal" for="remember-me">
            <input
              id="remember-me"
              v-model="form.rememberMe"
              type="checkbox"
              class="auth-option-minimal__input"
            />
            <span class="auth-option-minimal__box"></span>
            <span class="auth-option-minimal__label">记住登录</span>
          </label>

          <Button type="submit" class="auth-submit-minimal" :disabled="loading">
            {{ loading ? '验证中...' : '进入系统' }}
          </Button>

          <div class="auth-footer-minimal">
            <span>未登记访客？</span>
            <router-link to="/register" class="auth-link-minimal">申请访问权限</router-link>
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
import { Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()
const { login } = useUser()
const loading = ref(false)
const showPassword = ref(false)
const errorMessage = ref('')
const form = ref({
  email: '',
  password: '',
  rememberMe: false,
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
    const result = await login({
      email: form.value.email,
      password: form.value.password,
      remember_me: form.value.rememberMe,
    })
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
