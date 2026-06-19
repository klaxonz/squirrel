<template>
  <div class="min-h-full flex flex-col justify-center items-center bg-zinc-50 dark:bg-zinc-950 p-4 sm:p-8 relative">
    
    <!-- Main Content Container -->
    <main class="w-full max-w-[400px] bg-white dark:bg-zinc-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.1)] border border-border relative z-10 animate-in fade-in zoom-in-95 duration-300">
      
      <div class="p-6 sm:p-8">
        <!-- Header Area -->
        <header class="flex flex-col items-center text-center mb-8">
          <div class="h-12 w-12 bg-primary text-primary-foreground shadow-sm rounded-xl flex items-center justify-center mb-5">
            <AppIcon name="server" class="h-6 w-6" />
          </div>
          <h1 class="text-2xl font-semibold tracking-tight text-foreground mb-1.5">松鼠核心配置</h1>
          <p class="text-sm text-muted-foreground">连接至您的后端服务引擎</p>
        </header>

        <form @submit.prevent="handleConnect" class="space-y-5">
          <!-- Error Alert -->
          <Alert v-if="errorMessage" variant="error" class="animate-in slide-in-from-top-1">
            <AppIcon name="error" class="h-4 w-4" />
            <AlertDescription>{{ errorMessage }}</AlertDescription>
          </Alert>

          <!-- Server URL Field -->
          <div class="space-y-2">
            <label for="server-url" class="text-sm font-medium leading-none">
              服务器接口地址
            </label>
            <div class="relative">
              <Input
                id="server-url"
                v-model="form.serverUrl"
                type="url"
                required
                class="pr-24"
                placeholder="http://127.0.0.1:8001"
                :disabled="connecting"
                @input="clearStatus"
              />
              <div class="absolute right-1 top-1/2 -translate-y-1/2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  :disabled="!form.serverUrl.trim() || testing"
                  :loading="testing"
                  @click="handleTest"
                  class="h-8"
                >
                  {{ testing ? '测试中' : '测试连接' }}
                </Button>
              </div>
            </div>
            
            <!-- Test Result Feedback -->
            <div v-if="connectionMessage" :class="[
              'text-xs font-medium mt-1.5 flex items-center gap-1.5',
              testResult ? 'text-success' : 'text-destructive'
            ]">
              <AppIcon :name="testResult ? 'statusSuccess' : 'warning'" class="w-3.5 h-3.5" />
              {{ connectionMessage }}
            </div>
          </div>

          <!-- Quick Options -->
          <div class="space-y-4 pt-1">
            <div v-if="quickServerUrls.length" class="space-y-2.5">
              <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">常用地址</span>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="url in quickServerUrls"
                  :key="url"
                  type="button"
                  class="px-2.5 py-1 rounded-md border border-border bg-muted/50 text-xs font-medium text-muted-foreground hover:text-foreground hover:border-border/80 hover:bg-muted transition-colors"
                  @click="applyServerUrl(url)"
                >
                  {{ url }}
                </button>
              </div>
            </div>

            <div v-if="recentServerUrls.length" class="space-y-2.5">
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">最近连接</span>
                <button type="button" class="text-xs font-medium text-muted-foreground hover:text-destructive transition-colors" @click="handleClearRecent">
                  清空
                </button>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="url in recentServerUrls"
                  :key="url"
                  type="button"
                  class="px-2.5 py-1 rounded-md border border-border bg-muted/50 text-xs font-mono text-muted-foreground hover:text-foreground hover:border-border/80 hover:bg-muted transition-colors truncate max-w-[200px]"
                  @click="applyServerUrl(url)"
                  :title="url"
                >
                  {{ url }}
                </button>
              </div>
            </div>
          </div>

          <!-- Submit Button -->
          <div class="pt-4">
            <Button
              type="submit"
              class="w-full"
              size="lg"
              :loading="connecting"
              :disabled="!form.serverUrl.trim()"
            >
              {{ connecting ? '正在连接...' : '确认并进入系统' }}
            </Button>
          </div>
        </form>
      </div>
      
      <!-- Card Footer -->
      <div class="p-4 sm:p-6 bg-zinc-50/50 dark:bg-zinc-900/50 border-t border-border text-center flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
        <span class="text-sm text-muted-foreground">本地开发？</span>
        <button type="button" class="text-sm font-medium text-foreground hover:text-primary transition-colors underline decoration-border underline-offset-4 hover:decoration-primary" @click="fillLocalhost">
          快速切换至本机地址
        </button>
      </div>
    </main>

    <!-- Back link -->
    <router-link to="/login" class="mt-8 flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative z-10">
      <AppIcon name="back" class="w-4 h-4" /> 返回登录页面
    </router-link>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Logger } from '@/shared/lib/logger'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Alert, AlertDescription } from '@/shared/ui/alert'
import { useServerConfig } from '@/shared/composables/useServerConfig'

const router = useRouter()
const {
  getServerUrl,
  initServerConfig,
  recentServerUrls,
  setServerUrl,
  clearRecentServerUrls,
  testServerConnection,
} = useServerConfig()

const quickServerUrls = ['http://127.0.0.1:8001', 'http://localhost:8001']

const form = ref({
  serverUrl: '',
})

const connecting = ref(false)
const testing = ref(false)
const testResult = ref(null)
const errorMessage = ref('')
const connectionMessage = ref('')

const clearStatus = () => {
  testResult.value = null
  errorMessage.value = ''
  connectionMessage.value = ''
}

const fillLocalhost = () => {
  form.value.serverUrl = 'http://127.0.0.1:8001'
  clearStatus()
}

const applyServerUrl = (url) => {
  form.value.serverUrl = url
  clearStatus()
}

onMounted(async () => {
  await initServerConfig()
  form.value.serverUrl = getServerUrl() || ''
})

const handleClearRecent = () => {
  clearRecentServerUrls()
  clearStatus()
}

const handleTest = async () => {
  if (!form.value.serverUrl.trim()) return
  testing.value = true
  clearStatus()
  try {
    const result = await testServerConnection(form.value.serverUrl)
    testResult.value = result.ok
    connectionMessage.value = result.ok ? '后端服务响应正常' : '无法连接至该地址'
  } catch (err) {
    Logger.warn('[ServerConfig] Connection test failed', err)
    testResult.value = false
    connectionMessage.value = '测试失败，请检查网络'
  } finally {
    testing.value = false
  }
}

const handleConnect = async () => {
  if (!form.value.serverUrl.trim()) return
  connecting.value = true
  errorMessage.value = ''
  try {
    const ok = await setServerUrl(form.value.serverUrl)
    if (!ok) {
      errorMessage.value = '无效的服务器地址，请检查格式'
      return
    }
    await router.replace('/login')
  } catch (err) {
    Logger.warn('[ServerConfig] Connection failed', err)
    errorMessage.value = '连接失败，请重试'
  } finally {
    connecting.value = false
  }
}
</script>