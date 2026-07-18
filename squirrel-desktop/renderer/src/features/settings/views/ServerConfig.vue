<template>
  <AuthEntryCard
    title="归仓核心配置"
    description="连接至您的后端服务引擎"
    wide
  >
    <form novalidate class="auth-entry__form" @submit.prevent="handleConnect">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <AlertDescription>{{ errorMessage }}</AlertDescription>
        </Alert>
      </Transition>

      <div class="auth-field">
        <label for="server-url" class="auth-field__label">服务器接口地址</label>
        <div class="auth-server-field">
          <Input
            id="server-url"
            v-model="form.serverUrl"
            type="url"
            required
            placeholder="http://127.0.0.1:8001"
            :disabled="connecting"
            class="auth-field__input"
            @input="clearStatus"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="!form.serverUrl.trim() || testing"
            :loading="testing"
            @click="handleTest"
          >
            {{ testing ? '测试中' : '测试连接' }}
          </Button>
        </div>
        <p
          v-if="connectionMessage"
          class="auth-field__status"
          :class="testResult === null
            ? 'auth-field__status--idle'
            : testResult ? 'auth-field__status--success' : 'auth-field__status--error'"
        >
          <AppIcon
            :name="testResult === null
              ? 'info'
              : testResult ? 'statusSuccess' : 'warning'"
            class="auth-field__status-icon"
          />
          {{ connectionMessage }}
        </p>
      </div>

      <div v-if="quickServerUrls.length || recentServerUrls.length" class="auth-options">
        <div v-if="quickServerUrls.length" class="auth-options__group">
          <span class="auth-options__title">常用地址</span>
          <ul class="auth-options__list">
            <li v-for="url in quickServerUrls" :key="url">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="auth-options__chip"
                @click="applyServerUrl(url)"
              >
                <span class="auth-options__chip-text">{{ url }}</span>
              </Button>
            </li>
          </ul>
        </div>

        <div v-if="recentServerUrls.length" class="auth-options__group">
          <div class="auth-options__head">
            <span class="auth-options__title">最近连接</span>
            <Button type="button" variant="ghost" size="xs" @click="handleClearRecent">
              清空
            </Button>
          </div>
          <ul class="auth-options__list">
            <li v-for="url in recentServerUrls" :key="url">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="auth-options__chip"
                :title="url"
                @click="applyServerUrl(url)"
              >
                <span class="auth-options__chip-text">{{ url }}</span>
              </Button>
            </li>
          </ul>
        </div>
      </div>

      <Button
        type="submit"
        size="lg"
        :loading="connecting"
        :disabled="!form.serverUrl.trim()"
        class="auth-entry__submit"
      >
        {{ connecting ? '正在连接' : '确认并进入系统' }}
      </Button>
    </form>

    <template #footer>
      <span class="auth-entry__footer-text">本地开发？</span>
      <Button type="button" variant="link" size="sm" class="auth-entry__link" @click="fillLocalhost">
        快速切换至本机地址
      </Button>
    </template>

    <template #below>
      <router-link to="/login" class="auth-entry__back">
        <AppIcon name="back" class="h-3.5 w-3.5" />
        返回登录页面
      </router-link>
    </template>
  </AuthEntryCard>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthEntryCard from '@/features/auth/components/AuthEntryCard.vue'
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
