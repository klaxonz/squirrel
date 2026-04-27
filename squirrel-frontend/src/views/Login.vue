<template>
  <div class="auth-shell">
    <!-- Server Config Link -->
    <div class="auth-topbar">
      <router-link to="/server-config" class="auth-topbar__link">
        <span class="auth-topbar__eyebrow">Server</span>
        <span class="auth-topbar__value">{{ currentServerLabel }}</span>
      </router-link>
    </div>

    <div class="auth-layout">
      <!-- Left Panel: Branding -->
      <aside class="auth-sidebar">
        <h1 class="auth-sidebar__brand">SQRL</h1>
        <p class="auth-sidebar__tagline">
          视频订阅与管理平台。<br>
          统一管理多平台内容。
        </p>
        <div class="auth-sidebar__status">
          系统已就绪
        </div>
        <p v-if="currentServerUrl" class="auth-sidebar__server">
          {{ currentServerUrl }}
        </p>
      </aside>

      <!-- Right Panel: Form -->
      <main class="auth-main">
        <form class="auth-form-unified" @submit.prevent="handleSubmit">
          <!-- Header -->
          <div class="auth-form-header">
            <h2 class="auth-form-title">欢迎回来</h2>
            <p class="auth-form-subtitle">登录以继续使用 Squirrel</p>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="auth-error">
            {{ errorMessage }}
          </div>

          <!-- Email Field -->
          <div class="auth-field">
            <label for="email" class="auth-field__label">邮箱</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              class="auth-input"
              placeholder="your@email.com"
              autocomplete="email"
            />
          </div>

          <!-- Password Field -->
          <div class="auth-field">
            <label for="password" class="auth-field__label">密码</label>
            <div class="auth-password-wrapper">
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                class="auth-input"
                placeholder="Enter password"
                autocomplete="current-password"
              />
              <button
                type="button"
                class="auth-password-toggle"
                @click="showPassword = !showPassword"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
              >
                <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
              </button>
            </div>
          </div>

          <!-- Remember Me -->
          <label class="auth-checkbox">
            <input
              v-model="form.rememberMe"
              type="checkbox"
              class="auth-checkbox__input"
            />
            <span class="auth-checkbox__label">记住登录状态</span>
          </label>

          <!-- Submit Button -->
          <button
            type="submit"
            class="auth-submit"
            :disabled="loading"
          >
            {{ loading ? '验证中...' : '登录' }}
          </button>

          <!-- Footer Links -->
          <div class="auth-footer">
            <span>未注册？</span>
            <router-link to="/register" class="auth-link">申请访问权限</router-link>
          </div>
        </form>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import { useUser } from '../composables/useUser'
import { useServerConfig } from '@/composables/useServerConfig'

const router = useRouter()
const { login } = useUser()
const { initServerConfig, serverUrl: currentServerUrl } = useServerConfig()
const loading = ref(false)
const showPassword = ref(false)
const errorMessage = ref('')
const form = ref({
  email: '',
  password: '',
  rememberMe: false,
})

onMounted(async () => {
  await initServerConfig()
})

const currentServerLabel = computed(() => currentServerUrl.value || '未配置服务器')

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
