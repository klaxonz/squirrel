<template>
  <AuthEntryCard
    title="连接服务器"
    description="先保存 API 地址，再用该服务器上的账户进入归仓。"
    :show-server-action="false"
    stage="server"
  >
    <form class="auth-entry__form" @submit.prevent="handleConnect">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <div class="auth-field">
        <label for="server-url" class="auth-field__label">API 地址</label>
        <div class="auth-server-field">
          <Input
            fluid
            id="server-url"
            v-model="form.serverUrl"
            type="url"
            required
            size="lg"
            placeholder="http://127.0.0.1:8001"
            :disabled="busy"
            :aria-invalid="testResult === false || undefined"
            aria-describedby="server-url-feedback"
            class="auth-field__input"
            spellcheck="false"
            autocomplete="url"
            @input="clearStatus"
          />
          <Button
            type="button"
            severity="secondary"
            outlined
            size="lg"
            :disabled="!targetServerUrl || busy"
            :loading="testing"
            @click="handleTest"
          >
            {{ testing ? '测试中…' : '测试' }}
          </Button>
        </div>
        <p
          v-if="connectionMessage"
          id="server-url-feedback"
          role="status"
          aria-live="polite"
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
        <p v-else id="server-url-feedback" class="auth-field__hint">本地默认端口 8001</p>
      </div>

      <div v-if="addressSuggestions.length" class="auth-options">
        <div class="auth-options__head">
          <span class="auth-options__title">快捷填入</span>
          <Button
            v-if="recentServerUrls.length"
            type="button"
            text
            severity="secondary"
            size="sm"
            :disabled="busy"
            @click="handleClearRecent"
          >
            清空最近
          </Button>
        </div>
        <ul class="auth-options__list">
          <li v-for="url in addressSuggestions" :key="url">
            <Button
              type="button"
              severity="secondary"
              outlined
              size="sm"
              class="auth-chip"
              :class="{ 'auth-chip--active': form.serverUrl.trim() === url }"
              :title="url"
              :aria-pressed="form.serverUrl.trim() === url"
              :disabled="busy"
              @click="applyServerUrl(url)"
            >
              <span class="auth-chip__dot" aria-hidden="true" />
              <span class="auth-chip__text">{{ formatSuggestionLabel(url) }}</span>
            </Button>
          </li>
        </ul>
      </div>

      <Button
        type="submit"
        size="lg"
        :loading="connecting"
        :disabled="!targetServerUrl || busy"
        class="auth-entry__submit"
      >
        {{ connecting ? '正在保存…' : '保存并连接' }}
      </Button>
    </form>

    <template v-if="hasSavedServer" #footer>
      <span class="auth-entry__footer-text">已经配好了？</span>
      <router-link to="/login" class="auth-entry__link">直接登录</router-link>
    </template>
  </AuthEntryCard>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthEntryCard from '@/features/auth/components/AuthEntryCard.vue'
import { Logger } from '@/shared/lib/logger'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Alert } from '@/shared/ui/alert'
import { normalizeServerUrl, useServerConfig } from '@/shared/composables/useServerConfig'

const router = useRouter()
const {
  getServerUrl,
  serverUrl,
  initServerConfig,
  recentServerUrls,
  setServerUrl,
  clearRecentServerUrls,
  testServerConnection,
} = useServerConfig()

const PRESET_URLS = ['http://127.0.0.1:8001', 'http://localhost:8001']

const form = ref({ serverUrl: '' })
const connecting = ref(false)
const testing = ref(false)
const testResult = ref(null)
const errorMessage = ref('')
const connectionMessage = ref('')

const targetServerUrl = computed(() => normalizeServerUrl(form.value.serverUrl))
const hasSavedServer = computed(() => Boolean(serverUrl.value))
const busy = computed(() => testing.value || connecting.value)

const addressSuggestions = computed(() => {
  const seen = new Set()
  const out = []
  for (const url of [...PRESET_URLS, ...recentServerUrls.value]) {
    const key = url.trim()
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(key)
  }
  return out
})

const formatSuggestionLabel = (url) => {
  try {
    const host = new URL(url).host || url
    if (host.startsWith('127.0.0.1') || host.startsWith('localhost')) return host
    return host
  } catch {
    return url
  }
}

const clearStatus = () => {
  testResult.value = null
  errorMessage.value = ''
  connectionMessage.value = ''
}

const applyServerUrl = (url) => {
  form.value.serverUrl = url
  clearStatus()
}

onMounted(async () => {
  await initServerConfig()
  form.value.serverUrl = getServerUrl() || PRESET_URLS[0]
})

const handleClearRecent = () => {
  if (busy.value) return
  clearRecentServerUrls()
  clearStatus()
}

const handleTest = async () => {
  if (busy.value) return
  const targetUrl = targetServerUrl.value
  if (!targetUrl) {
    testResult.value = false
    connectionMessage.value = '请输入有效的 HTTP 或 HTTPS 地址'
    return
  }
  testing.value = true
  clearStatus()
  try {
    const result = await testServerConnection(targetUrl)
    if (targetServerUrl.value !== targetUrl) return
    testResult.value = result.ok
    connectionMessage.value = result.ok ? '连接正常，可以继续' : result.message
  } catch (err) {
    Logger.warn('[ServerConfig] Connection test failed', err)
    testResult.value = false
    connectionMessage.value = '测试失败，请检查网络或地址'
  } finally {
    testing.value = false
  }
}

const handleConnect = async () => {
  if (busy.value) return
  const targetUrl = targetServerUrl.value
  if (!targetUrl) {
    testResult.value = false
    connectionMessage.value = '请输入有效的 HTTP 或 HTTPS 地址'
    return
  }
  connecting.value = true
  errorMessage.value = ''
  connectionMessage.value = '正在验证服务器…'
  testResult.value = null
  try {
    const connection = await testServerConnection(targetUrl)
    if (!connection.ok) {
      testResult.value = false
      connectionMessage.value = connection.message
      return
    }

    testResult.value = true
    connectionMessage.value = '连接正常，正在保存…'
    const ok = await setServerUrl(targetUrl)
    if (!ok) {
      errorMessage.value = '地址格式无效，请检查后重试'
      return
    }
    await router.replace('/login')
  } catch (err) {
    Logger.warn('[ServerConfig] Connection failed', err)
    errorMessage.value = '保存失败，请重试'
  } finally {
    connecting.value = false
  }
}
</script>
