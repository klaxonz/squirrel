<template>
  <div class="min-h-[100dvh] flex flex-col justify-center items-center bg-muted/20 p-4 sm:p-8 relative overflow-hidden">
    <!-- Subtle Background Decoration -->
    <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>

    <!-- Server Config Pill -->
    <div class="absolute top-4 right-4 sm:top-8 sm:right-8 z-20">
      <router-link 
        to="/server-config" 
        class="inline-flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm rounded-full bg-background/80 backdrop-blur border border-border hover:border-primary/50 hover:text-primary transition-colors shadow-sm"
      >
        <AppIcon name="server" class="h-4 w-4 opacity-70" />
        <span class="opacity-70 hidden sm:inline">服务器:</span>
        <span class="font-medium truncate max-w-[120px]">{{ currentServerLabel }}</span>
      </router-link>
    </div>

    <!-- Main Content Container -->
    <main class="w-full max-w-[400px] relative z-10">
      
      <!-- Header Area -->
      <header class="flex flex-col items-center text-center mb-8">
        <div class="h-14 w-14 bg-background border border-border/50 text-primary shadow-sm rounded-2xl flex items-center justify-center mb-5">
          <AppIcon name="brand" class="h-8 w-8" />
        </div>
        <h1 class="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground mb-2">加入松鼠</h1>
        <p class="text-sm text-muted-foreground">创建账户，开始管理您的内容订阅</p>
      </header>

      <!-- Auth Card -->
      <div class="bg-card border border-border rounded-xl shadow-sm overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div class="p-6 sm:p-8">
          <form @submit.prevent="handleSubmit" class="space-y-4">
            
            <!-- Error Alert -->
            <div 
              v-if="errorMessage" 
              class="p-3 text-sm text-error bg-error/10 border border-error/20 rounded-md flex items-start gap-2.5 animate-in slide-in-from-top-1 mb-2"
            >
              <AppIcon name="error" class="h-4 w-4 shrink-0 mt-0.5" />
              <span class="leading-relaxed">{{ errorMessage }}</span>
            </div>

            <!-- Nickname Field -->
            <div class="space-y-2">
              <label for="nickname" class="text-sm font-medium leading-none">
                昵称
              </label>
              <input
                id="nickname"
                v-model="form.nickname"
                type="text"
                required
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                placeholder="您希望被称呼的名字"
                autocomplete="nickname"
              />
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
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                placeholder="name@example.com"
                autocomplete="email"
              />
            </div>

            <!-- Password Field -->
            <div class="space-y-2">
              <label for="password" class="text-sm font-medium leading-none">
                密码
              </label>
              <div class="relative">
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors pr-10"
                  placeholder="至少输入 8 位字符"
                  autocomplete="new-password"
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

            <!-- Submit Button -->
            <div class="pt-4">
              <button
                type="submit"
                class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 w-full shadow-sm"
                :disabled="loading"
              >
                <AppIcon v-if="loading" name="loadingSpinner" class="mr-2 h-4 w-4 animate-spin" />
                {{ loading ? '正在注册...' : '创建账户' }}
              </button>
            </div>
          </form>
        </div>
        
        <!-- Card Footer -->
        <div class="p-4 sm:p-6 bg-muted/30 border-t border-border text-center flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
          <span class="text-sm text-muted-foreground">已有账户？</span>
          <router-link to="/login" class="text-sm font-medium text-foreground hover:text-primary transition-colors underline decoration-border underline-offset-4 hover:decoration-primary">
            直接登录
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
