<template>
  <AuthEntryCard
    title="连接服务器"
    description="验证 API 端点后再保存。服务器决定账户、媒体与同步数据的来源。"
    :show-server-action="false"
    stage="server"
  >
    <form class="auth-entry__form server-setup" @submit.prevent="handleConnect">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <AppFormField
        id="server-url"
        label="API 地址"
        description="仅支持 HTTP 或 HTTPS，路径会被规范化为服务器根地址。"
        :error="testResult === false ? connectionMessage : ''"
        required
      >
        <template #default="{ id, control }">
          <div class="auth-server-field">
            <Input
              v-bind="control"
              :id="id"
              v-model="form.serverUrl"
              fluid
              type="url"
              size="lg"
              placeholder="http://127.0.0.1:8001"
              :disabled="busy"
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
              {{ testing ? '测试中…' : '测试连接' }}
            </Button>
          </div>
        </template>
      </AppFormField>

      <section v-if="targetServerUrl" class="server-target" aria-label="目标服务器">
        <div class="server-target__identity">
          <span class="server-target__status" :class="serverStatusClass" aria-hidden="true" />
          <div class="server-target__copy">
            <strong>{{ targetHost }}</strong>
            <span>{{ targetProtocolLabel }} · {{ targetServerUrl }}</span>
          </div>
          <span class="server-target__state">{{ serverStatusLabel }}</span>
        </div>

        <p
          v-if="connectionMessage && testResult !== false"
          id="server-connection-status"
          role="status"
          aria-live="polite"
          class="server-target__message"
          :class="testResult ? 'is-success' : ''"
        >
          <AppIcon :name="testResult ? 'statusSuccess' : 'info'" class="size-4" />
          {{ connectionMessage }}
        </p>

        <Alert v-if="isInsecureRemote" variant="warning" class="server-target__warning">
          <AppIcon name="warning" class="size-4" />
          <p>该远程地址使用 HTTP，登录凭据和媒体请求可能以明文传输。生产环境应使用 HTTPS。</p>
        </Alert>
      </section>

      <section v-if="addressSuggestions.length" class="server-list" aria-labelledby="server-list-title">
        <header class="server-list__header">
          <div>
            <h2 id="server-list-title">可用地址</h2>
            <p>本机预设与最近成功保存的服务器。</p>
          </div>
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
        </header>
        <ul class="server-list__items">
          <li v-for="url in addressSuggestions" :key="url">
            <button
              type="button"
              class="server-list__option"
              :class="{ 'is-active': targetServerUrl === normalizeServerUrl(url) }"
              :aria-pressed="targetServerUrl === normalizeServerUrl(url)"
              :disabled="busy"
              @click="applyServerUrl(url)"
            >
              <span class="server-list__option-icon" aria-hidden="true">
                <AppIcon :name="isLocalServer(url) ? 'server' : 'globe'" class="size-4" />
              </span>
              <span class="server-list__option-copy">
                <strong>{{ formatSuggestionLabel(url) }}</strong>
                <span>{{ url }}</span>
              </span>
              <span class="server-list__option-kind">{{ isLocalServer(url) ? '本机' : '最近' }}</span>
              <AppIcon name="chevronRight" class="size-4 text-muted-foreground" />
            </button>
          </li>
        </ul>
      </section>

      <div class="server-setup__commit">
        <p>{{ commitHint }}</p>
        <Button
          type="submit"
          size="lg"
          :loading="connecting"
          :disabled="!targetServerUrl || busy"
          class="auth-entry__submit"
        >
          {{ connecting ? '正在验证并保存…' : '验证并保存' }}
        </Button>
      </div>
    </form>

    <template v-if="hasSavedServer" #footer>
      <span class="auth-entry__footer-text">保留当前服务器？</span>
      <router-link to="/login" class="auth-entry__link">直接登录</router-link>
    </template>
  </AuthEntryCard>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthEntryCard from '@/features/auth/components/AuthEntryCard.vue'
import AppFormField from '@/shared/components/layout/AppFormField.vue'
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
const testedServerUrl = ref('')
const errorMessage = ref('')
const connectionMessage = ref('')

const targetServerUrl = computed(() => normalizeServerUrl(form.value.serverUrl))
const targetUrl = computed(() => {
  try {
    return targetServerUrl.value ? new URL(targetServerUrl.value) : null
  } catch {
    return null
  }
})
const targetHost = computed(() => targetUrl.value?.host || '地址格式无效')
const targetProtocolLabel = computed(() => targetUrl.value?.protocol === 'https:' ? 'HTTPS 加密' : 'HTTP')
const hasSavedServer = computed(() => Boolean(serverUrl.value))
const busy = computed(() => testing.value || connecting.value)
const isTestCurrent = computed(() => Boolean(targetServerUrl.value && testedServerUrl.value === targetServerUrl.value))
const isInsecureRemote = computed(() => {
  if (targetUrl.value?.protocol !== 'http:') return false
  return !isLocalHostname(targetUrl.value.hostname)
})
const serverStatusClass = computed(() => {
  if (!isTestCurrent.value || testResult.value === null) return 'is-idle'
  return testResult.value ? 'is-success' : 'is-error'
})
const serverStatusLabel = computed(() => {
  if (testing.value) return '测试中'
  if (!isTestCurrent.value || testResult.value === null) return '尚未验证'
  return testResult.value ? '连接正常' : '连接失败'
})
const commitHint = computed(() => {
  if (isTestCurrent.value && testResult.value === true) return '连接已经验证。保存后将进入该服务器的登录页。'
  return '保存时会再次验证当前地址，不会写入不可达的服务器。'
})

const addressSuggestions = computed(() => {
  const seen = new Set()
  const out = []
  for (const url of [...PRESET_URLS, ...recentServerUrls.value]) {
    const key = normalizeServerUrl(url)
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(key)
  }
  return out
})

const isLocalHostname = (hostname) => {
  const value = String(hostname || '').toLowerCase()
  return value === 'localhost' || value === '127.0.0.1' || value === '::1' || value.endsWith('.localhost')
}

const isLocalServer = (url) => {
  try {
    return isLocalHostname(new URL(url).hostname)
  } catch {
    return false
  }
}

const formatSuggestionLabel = (url) => {
  try {
    return new URL(url).host || url
  } catch {
    return url
  }
}

const clearStatus = () => {
  testResult.value = null
  testedServerUrl.value = ''
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
  const targetUrlValue = targetServerUrl.value
  if (!targetUrlValue) {
    testResult.value = false
    connectionMessage.value = '请输入有效的 HTTP 或 HTTPS 地址'
    return
  }
  testing.value = true
  clearStatus()
  try {
    const result = await testServerConnection(targetUrlValue)
    if (targetServerUrl.value !== targetUrlValue) return
    testedServerUrl.value = targetUrlValue
    testResult.value = result.ok
    connectionMessage.value = result.ok ? '服务器已响应，可以安全地继续保存。' : result.message
  } catch (err) {
    Logger.warn('[ServerConfig] Connection test failed', err)
    if (targetServerUrl.value !== targetUrlValue) return
    testedServerUrl.value = targetUrlValue
    testResult.value = false
    connectionMessage.value = '测试失败，请检查网络或地址'
  } finally {
    testing.value = false
  }
}

const handleConnect = async () => {
  if (busy.value) return
  const targetUrlValue = targetServerUrl.value
  if (!targetUrlValue) {
    testResult.value = false
    connectionMessage.value = '请输入有效的 HTTP 或 HTTPS 地址'
    return
  }
  connecting.value = true
  errorMessage.value = ''
  connectionMessage.value = '正在验证服务器…'
  testResult.value = null
  testedServerUrl.value = targetUrlValue
  try {
    const connection = await testServerConnection(targetUrlValue)
    if (targetServerUrl.value !== targetUrlValue) return
    if (!connection.ok) {
      testResult.value = false
      connectionMessage.value = connection.message
      return
    }

    testResult.value = true
    connectionMessage.value = '连接正常，正在保存…'
    const ok = await setServerUrl(targetUrlValue)
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

<style scoped>
.server-setup {
  gap: var(--space-5);
}

.server-target,
.server-list {
  border-top: 1px solid hsl(var(--border));
  padding-top: var(--space-4);
}

.server-target {
  display: grid;
  gap: var(--space-3);
}

.server-target__identity {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
}

.server-target__status {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.4);
}

.server-target__status.is-success {
  background: hsl(var(--success));
}

.server-target__status.is-error {
  background: hsl(var(--destructive));
}

.server-target__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.server-target__copy strong,
.server-list__option-copy strong {
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.server-target__copy span,
.server-list__option-copy span,
.server-list__header p,
.server-setup__commit p {
  margin: 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.server-target__state,
.server-list__option-kind {
  flex: none;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

.server-target__message {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.server-target__message.is-success {
  color: hsl(var(--success));
}

.server-target__warning {
  align-items: flex-start;
}

.server-list__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.server-list__header h2 {
  margin: 0 0 0.2rem;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 700;
}

.server-list__items {
  display: grid;
  gap: 1px;
  margin: 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--border));
  list-style: none;
}

.server-list__option {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: 2rem minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-2);
  border: 0;
  padding: 0.625rem;
  background: hsl(var(--card));
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.server-list__option:hover,
.server-list__option:focus-visible,
.server-list__option.is-active {
  background: hsl(var(--accent));
}

.server-list__option:focus-visible {
  position: relative;
  outline: 2px solid hsl(var(--ring));
  outline-offset: -2px;
}

.server-list__option-icon {
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
}

.server-list__option-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.15rem;
}

.server-setup__commit {
  display: grid;
  gap: var(--space-3);
}

.server-setup__commit p {
  white-space: normal;
}

@media (max-width: 520px) {
  .server-target__identity {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .server-target__state {
    grid-column: 2;
  }

  .server-list__option {
    grid-template-columns: 2rem minmax(0, 1fr) auto;
  }

  .server-list__option-kind {
    display: none;
  }
}
</style>
