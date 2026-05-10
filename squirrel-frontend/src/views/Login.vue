<template>
  <div class="min-h-[100dvh] bg-background flex text-foreground">
    <!-- Left Panel: Branding (Hidden on mobile) -->
    <aside class="hidden lg:flex lg:w-1/2 xl:w-5/12 bg-muted flex-col justify-between p-12 border-r border-border relative overflow-hidden">
      <!-- Optional decorative gradient background -->
      <div class="absolute inset-0 bg-gradient-to-br from-primary/10 via-background/5 to-background pointer-events-none"></div>
      
      <div class="relative z-10">
        <h1 class="text-4xl font-bold tracking-tight mb-4 flex items-center gap-3">
          <AppIcon name="brand" class="h-8 w-8 text-primary" />
          松鼠
        </h1>
        <p class="text-lg text-muted-foreground max-w-md leading-relaxed">
          视频订阅与管理平台。<br>
          统一管理多平台内容，打造您的专属内容库。
        </p>
      </div>

      <div class="relative z-10">
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-background/80 backdrop-blur border border-border/50 text-sm font-medium shadow-sm">
          <div class="h-2 w-2 rounded-full bg-success"></div>
          系统已就绪
        </div>
        <p v-if="currentServerUrl" class="mt-4 text-sm text-muted-foreground font-mono bg-background/50 inline-block px-2 py-1 rounded">
          {{ currentServerUrl }}
        </p>
      </div>
    </aside>

    <!-- Right Panel: Form -->
    <main class="flex-1 flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-16 xl:px-24">
      <div class="mx-auto w-full max-w-sm lg:max-w-md relative">
        
        <!-- Server Config Link -->
        <div class="absolute right-0 -top-16 lg:-top-24">
          <router-link 
            to="/server-config" 
            class="inline-flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm rounded-full bg-background border border-border hover:border-primary/50 hover:text-primary transition-colors shadow-sm"
          >
            <AppIcon name="server" class="h-4 w-4 opacity-70" />
            <span class="opacity-70 hidden sm:inline">当前服务器:</span>
            <span class="font-medium truncate max-w-[150px]">{{ currentServerLabel }}</span>
          </router-link>
        </div>

        <!-- Header -->
        <div class="mb-8">
          <h2 class="text-3xl font-semibold tracking-tight">欢迎回来</h2>
          <p class="text-muted-foreground mt-2 text-sm sm:text-base">登录您的账户以继续使用松鼠</p>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- Error Alert -->
          <div 
            v-if="errorMessage" 
            class="p-4 text-sm text-error bg-error/10 border border-error/20 rounded-lg flex items-start gap-3 animate-in fade-in slide-in-from-top-2"
          >
            <AppIcon name="error" class="h-5 w-5 shrink-0 mt-0.5" />
            <span class="leading-relaxed">{{ errorMessage }}</span>
          </div>

          <div class="space-y-4">
            <!-- Email Field -->
            <div class="space-y-2">
              <label for="email" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                邮箱
              </label>
              <input
                id="email"
                v-model="form.email"
                type="email"
                required
                class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
                placeholder="name@example.com"
                autocomplete="email"
              />
            </div>

            <!-- Password Field -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label for="password" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  密码
                </label>
              </div>
              <div class="relative">
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200 pr-10"
                  placeholder="请输入您的密码"
                  autocomplete="current-password"
                />
                <button
                  type="button"
                  class="absolute right-1 top-1 h-9 w-9 flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  @click="showPassword = !showPassword"
                  :title="showPassword ? '隐藏密码' : '显示密码'"
                >
                  <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          <!-- Remember Me -->
          <div class="flex items-center space-x-2">
            <input
              id="rememberMe"
              v-model="form.rememberMe"
              type="checkbox"
              class="h-4 w-4 shrink-0 rounded-[4px] border border-primary text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 accent-primary cursor-pointer"
            />
            <label
              for="rememberMe"
              class="text-sm font-medium leading-none cursor-pointer select-none"
            >
              记住登录状态
            </label>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-md h-11 px-8 w-full"
            :disabled="loading"
          >
            <AppIcon v-if="loading" name="loadingSpinner" class="mr-2 h-4 w-4 animate-spin" />
            {{ loading ? '验证中...' : '登录' }}
          </button>
        </form>

        <!-- Footer -->
        <div class="mt-8 text-center text-sm text-muted-foreground">
          还没有账户？
          <router-link to="/register" class="font-medium text-foreground hover:text-primary underline underline-offset-4 decoration-border hover:decoration-primary transition-all duration-200">
            申请访问权限
          </router-link>
        </div>
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
