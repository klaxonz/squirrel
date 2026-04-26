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
          创建新账户。<br>
          加入视频订阅网络。
        </p>
        <div class="auth-sidebar__status">
          账户注册
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
            <h2 class="auth-form-title">创建账户</h2>
            <p class="auth-form-subtitle">填写以下信息完成注册</p>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="auth-error">
            {{ errorMessage }}
          </div>

          <!-- Nickname Field -->
          <div class="auth-field">
            <label for="nickname" class="auth-field__label">昵称</label>
            <input
              id="nickname"
              v-model="form.nickname"
              type="text"
              required
              class="auth-input"
              placeholder="Your name"
              autocomplete="nickname"
            />
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
                placeholder="At least 8 characters"
                autocomplete="new-password"
              />
              <button
                type="button"
                class="auth-password-toggle"
                @click="showPassword = !showPassword"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
              >
                <component :is="showPassword ? EyeOff : Eye" class="h-4 w-4" />
              </button>
            </div>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            class="auth-submit"
            :disabled="loading"
          >
            {{ loading ? '注册中...' : '创建账户' }}
          </button>

          <!-- Footer Links -->
          <div class="auth-footer">
            <span>已有账户？</span>
            <router-link to="/login" class="auth-link">直接登录</router-link>
          </div>
        </form>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '../composables/useUser'
import { useServerConfig } from '@/composables/useServerConfig'
import { Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()
const { register } = useUser()
const { initServerConfig, serverUrl: currentServerUrl } = useServerConfig()
const loading = ref(false)
const showPassword = ref(false)
const errorMessage = ref('')
const form = ref({
  nickname: '',
  email: '',
  password: '',
})

onMounted(async () => {
  await initServerConfig()
})

const currentServerLabel = computed(() => currentServerUrl.value || '未配置服务器')

const getErrorMessage = (error) => {
  if (!error) return '注册失败，请稍后再试。'
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string') return error.message
  if (typeof error?.detail === 'string') return error.detail
  if (typeof error?.response?.data?.detail === 'string') return error.response.data.detail
  return '注册失败，请检查输入内容后重试。'
}

const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const result = await register(form.value)
    if (result.error) {
      errorMessage.value = getErrorMessage(result.error)
      return
    }

    await router.push('/login')
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="../styles/views/auth-entry.css"></style>
