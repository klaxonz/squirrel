<template>
  <div class="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
    <!-- Logo/Brand Area -->
    <div class="mb-10 text-center space-y-2">
      <div class="w-12 h-12 bg-slate-900 rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg">
        <Network class="w-6 h-6 text-white" />
      </div>
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">SQRL 核心配置</h1>
      <p class="text-sm text-slate-500">连接至您的后端服务引擎</p>
    </div>

    <!-- Main Config Card -->
    <div class="w-full max-w-md bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.1),0_10px_20px_-5px_rgba(0,0,0,0.04)] border border-slate-200 overflow-hidden">
      <form class="p-8 space-y-8" @submit.prevent="handleConnect">
        <!-- Error Alert -->
        <div v-if="errorMessage" class="p-4 rounded-lg bg-rose-50 border border-rose-100 flex items-center gap-3 text-sm text-rose-700 animate-in fade-in zoom-in-95">
          <AlertCircle class="w-4 h-4 shrink-0" />
          {{ errorMessage }}
        </div>

        <!-- Server URL Field -->
        <div class="space-y-2">
          <label for="server-url" class="text-[11px] font-bold text-slate-400 uppercase tracking-wider ml-1">服务器 API 地址</label>
          <div class="relative group">
            <Input
              id="server-url"
              v-model="form.serverUrl"
              type="url"
              required
              class="h-12 pl-4 pr-24 bg-white border-slate-200 rounded-xl text-base focus-visible:ring-slate-200 shadow-none w-full transition-all"
              placeholder="http://127.0.0.1:8001"
              :disabled="connecting"
              @input="clearStatus"
            />
            <div class="absolute right-2 top-1/2 -translate-y-1/2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="!form.serverUrl.trim() || testing"
                @click="handleTest"
                class="h-8 px-3 text-xs font-bold text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
              >
                <RefreshCw v-if="testing" class="w-3.5 h-3.5 animate-spin mr-1.5" />
                {{ testing ? '测试中' : '测试连接' }}
              </Button>
            </div>
          </div>
          
          <!-- Test Result Feedback -->
          <div v-if="connectionMessage" :class="[
            'text-[11px] font-bold mt-2 px-2 flex items-center gap-1.5',
            testResult ? 'text-emerald-600' : 'text-rose-600'
          ]">
            <CheckCircle2 v-if="testResult" class="w-3 h-3" />
            <AlertCircle v-else class="w-3 h-3" />
            {{ connectionMessage }}
          </div>
        </div>

        <!-- Quick Options -->
        <div class="space-y-4">
          <div v-if="quickServerUrls.length" class="space-y-2">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">常用地址</span>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="url in quickServerUrls"
                :key="url"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-100 bg-slate-50 text-xs font-medium text-slate-600 hover:border-slate-300 hover:bg-slate-100 transition-all"
                @click="applyServerUrl(url)"
              >
                {{ url }}
              </button>
            </div>
          </div>

          <div v-if="recentServerUrls.length" class="space-y-2">
            <div class="flex items-center justify-between px-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">最近连接</span>
              <button type="button" class="text-[10px] font-bold text-slate-400 hover:text-rose-500 uppercase tracking-widest" @click="handleClearRecent">
                清空
              </button>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="url in recentServerUrls"
                :key="url"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-100 bg-slate-50 text-xs font-mono text-slate-500 hover:border-slate-300 hover:bg-slate-100 transition-all"
                @click="applyServerUrl(url)"
              >
                {{ url }}
              </button>
            </div>
          </div>
        </div>

        <!-- Submit -->
        <div class="pt-2">
          <Button
            type="submit"
            class="w-full h-12 bg-slate-900 text-white hover:bg-slate-800 rounded-xl font-bold text-base shadow-lg shadow-slate-900/10 transition-all"
            :disabled="connecting || !form.serverUrl.trim()"
          >
            <span v-if="connecting" class="flex items-center gap-2">
              <RefreshCw class="w-4 h-4 animate-spin" />
              正在连接...
            </span>
            <span v-else>确认并进入系统</span>
          </Button>
        </div>
      </form>

      <!-- Footer -->
      <div class="px-8 py-5 bg-slate-50 border-t border-slate-100 flex items-center justify-center gap-2">
        <span class="text-xs text-slate-400">本地开发？</span>
        <button type="button" class="text-xs font-bold text-slate-600 hover:text-slate-900 underline underline-offset-4" @click="fillLocalhost">
          快速切换至 Localhost
        </button>
      </div>
    </div>

    <!-- Back link -->
    <router-link to="/login" class="mt-8 flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-slate-600 transition-colors">
      <ArrowLeft class="w-4 h-4" /> 返回登录页面
    </router-link>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Network, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  ArrowLeft 
} from 'lucide-vue-next'
import { useServerConfig } from '@/composables/useServerConfig'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

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
  } catch {
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
  } catch {
    errorMessage.value = '连接失败，请重试'
  } finally {
    connecting.value = false
  }
}
</script>

<style scoped>
.animate-in {
  animation-duration: 0.3s;
}
</style>
