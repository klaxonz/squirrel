<template>
  <div class="min-h-[100dvh] flex flex-col justify-center items-center bg-zinc-50 dark:bg-zinc-950 p-4 sm:p-8 relative">
    
    <!-- Server Config Pill -->
    <div class="absolute top-4 right-4 sm:top-8 sm:right-8 z-20">
      <router-link 
        to="/server-config" 
        class="inline-flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm rounded-full bg-white dark:bg-zinc-900 border border-border hover:border-primary/50 hover:text-primary transition-colors shadow-sm"
      >
        <AppIcon name="server" class="h-4 w-4 opacity-70" />
        <span class="opacity-70 hidden sm:inline">服务器:</span>
        <span class="font-medium truncate max-w-[120px]">{{ currentServerLabel }}</span>
      </router-link>
    </div>

    <!-- Main Content Container -->
    <main class="w-full max-w-[400px] bg-white dark:bg-zinc-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.1)] border border-border relative z-10 animate-in fade-in zoom-in-95 duration-300">
      
      <div class="p-6 sm:p-8">
        <!-- Header Area -->
        <header class="flex flex-col items-center text-center mb-8">
          <div class="h-12 w-12 bg-primary text-primary-foreground shadow-sm rounded-xl flex items-center justify-center mb-5">
            <AppIcon name="brand" class="h-6 w-6" />
          </div>
          <h1 class="text-2xl font-semibold tracking-tight text-foreground mb-1.5">欢迎回来</h1>
          <p class="text-sm text-muted-foreground">登录您的账户以继续使用松鼠</p>
        </header>

        <form @submit.prevent="handleSubmit" class="space-y-5">
          <!-- Error Alert -->
          <div 
            v-if="errorMessage" 
            class="p-3 text-sm text-error bg-error/10 border border-error/20 rounded-md flex items-start gap-2.5 animate-in slide-in-from-top-1"
          >
            <AppIcon name="error" class="h-4 w-4 shrink-0 mt-0.5" />
            <span class="leading-relaxed">{{ errorMessage }}</span>
          </div>

          <!-- Email Field -->
          <div class="space-y-2">
            <label for="email" class="text-sm font-medium leading-none">
              邮箱
            </label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              class="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              placeholder="name@example.com"
              autocomplete="email"
            />
          </div>

          <!-- Password Field -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label for="password" class="text-sm font-medium leading-none">
                密码
              </label>
            </div>
            <div class="relative">
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                class="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors pr-10"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
              <button
                type="button"
                class="absolute right-1 top-0.5 h-9 w-9 flex items-center justify-center text-muted-foreground hover:text-foreground rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                @click="showPassword = !showPassword"
                :title="showPassword ? '隐藏密码' : '显示密码'"
              >
                <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
              </button>
            </div>
          </div>

          <!-- Remember Me & Submit -->
          <div class="pt-2">
            <div class="flex items-center space-x-2 mb-6">
              <input
                id="rememberMe"
                v-model="form.rememberMe"
                type="checkbox"
                class="h-4 w-4 shrink-0 rounded-[4px] border border-input bg-transparent text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50 accent-primary cursor-pointer transition-colors"
              />
              <label
                for="rememberMe"
                class="text-sm font-medium leading-none cursor-pointer select-none text-muted-foreground hover:text-foreground transition-colors"
              >
                保持登录状态
              </label>
            </div>

            <button
              type="submit"
              class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 w-full shadow-sm"
              :disabled="loading"
            >
              <AppIcon v-if="loading" name="loadingSpinner" class="mr-2 h-4 w-4 animate-spin" />
              {{ loading ? '正在登录...' : '登录' }}
            </button>
          </div>
        </form>
      </div>
      
      <!-- Card Footer -->
      <div class="p-4 sm:p-6 bg-zinc-50/50 dark:bg-zinc-900/50 border-t border-border text-center flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
        <span class="text-sm text-muted-foreground">还没有账户？</span>
        <router-link to="/register" class="text-sm font-medium text-foreground hover:text-primary transition-colors underline decoration-border underline-offset-4 hover:decoration-primary">
          创建新账户
        </router-link>
      </div>
    </main>
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