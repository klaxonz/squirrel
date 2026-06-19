<template>
  <div class="min-h-full flex flex-col justify-center items-center bg-zinc-50 dark:bg-zinc-950 p-4 sm:p-8 relative">
    
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
          <h1 class="text-2xl font-semibold tracking-tight text-foreground mb-1.5">加入松鼠</h1>
          <p class="text-sm text-muted-foreground">创建账户，开始管理您的内容订阅</p>
        </header>

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
              class="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
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
              class="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
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
                class="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors pr-10"
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
      <div class="p-4 sm:p-6 bg-zinc-50/50 dark:bg-zinc-900/50 border-t border-border text-center flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
        <span class="text-sm text-muted-foreground">已有账户？</span>
        <router-link to="/login" class="text-sm font-medium text-foreground hover:text-primary transition-colors underline decoration-border underline-offset-4 hover:decoration-primary">
          直接登录
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import { useUserStore } from '@/stores/user'
import { useServerConfig } from '@/composables/useServerConfig'

const router = useRouter()
const userStore = useUserStore()
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

// ponytail: userStore.register never throws (handleRequest swallows axios errors
// into RequestResult.error), so there's no catch — error surfaces via result.error.
const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  const result = await userStore.register(form.value)
  loading.value = false
  if (result.error) {
    errorMessage.value = result.error.message
    return
  }

  await router.push('/login')
}
</script>