<template>
  <div class="auth-shell">
    <div class="auth-topbar">
      <router-link to="/server-config" class="auth-topbar__link">
        <span>
          <span class="auth-topbar__eyebrow">Server</span>
          <span class="auth-topbar__value">{{ currentServerLabel }}</span>
        </span>
      </router-link>
    </div>

    <div class="auth-divider-line"></div>

    <div class="auth-layout">
      <!-- 左侧：品牌展示区 -->
      <aside class="auth-sidebar">
        <div class="auth-sidebar__status">创建新身份</div>
        <h1 class="auth-sidebar__brand">SQRL</h1>
        <p v-if="currentServerUrl" class="auth-sidebar__server">
          已连接至 {{ currentServerUrl }}
        </p>
        <div class="auth-sidebar__status" style="margin-top: auto; opacity: 0.1">00:00:00 // 加入网络</div>
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
              id="nickname"
              v-model="form.nickname"
              type="text"
              required
              placeholder=" "
              class="auth-input-minimal"
            />
            <label for="nickname" class="auth-label-floating">昵称</label>
          </div>

          <div class="auth-field-minimal">
            <span class="auth-field-index">02</span>
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
            <span class="auth-field-index">03</span>
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

          <Button type="submit" class="auth-submit-minimal" :disabled="loading">
            {{ loading ? '初始化中...' : '注册身份' }}
          </Button>

          <div class="auth-footer-minimal">
            <span>已完成同步？</span>
            <router-link to="/login" class="auth-link-minimal">直接登入</router-link>
          </div>

          <div class="auth-footer-minimal">
            <span>服务器不对？</span>
            <router-link to="/server-config" class="auth-link-minimal">切换服务器</router-link>
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
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
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

const currentServerLabel = computed(() => currentServerUrl.value || '切换服务器')

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

<style scoped>
.auth-sidebar__server {
  margin-top: 0.75rem;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.08em;
  word-break: break-all;
}
</style>
