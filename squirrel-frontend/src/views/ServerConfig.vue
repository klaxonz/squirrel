<template>
  <div class="auth-shell">
    <div class="auth-topbar">
      <router-link to="/login" class="auth-topbar__link">
        <span>
          <span class="auth-topbar__eyebrow">Auth</span>
          <span class="auth-topbar__value">{{ currentServerLabel }}</span>
        </span>
      </router-link>
    </div>

    <div class="auth-divider-line"></div>

    <div class="auth-layout">
      <aside class="auth-sidebar">
        <div class="auth-sidebar__status">网络初始化</div>
        <h1 class="auth-sidebar__brand">SQRL</h1>
        <p class="auth-sidebar__desc">连接至后端服务器</p>
        <div class="auth-sidebar__hint">
          <div class="hint-item">
            <span class="hint-marker">01</span>
            <span>输入服务器地址</span>
          </div>
          <div class="hint-item">
            <span class="hint-marker">02</span>
            <span>测试连接</span>
          </div>
          <div class="hint-item">
            <span class="hint-marker">03</span>
            <span>进入系统</span>
          </div>
        </div>
        <div class="auth-sidebar__status" style="margin-top: auto; opacity: 0.1">00:00:00 // 节点连接</div>
      </aside>

      <main class="auth-main">
        <form class="auth-form-minimal" @submit.prevent="handleConnect">
          <Alert v-if="errorMessage" variant="destructive" class="auth-error-minimal mb-8">
            <AlertDescription>{{ errorMessage }}</AlertDescription>
          </Alert>

          <div class="auth-field-minimal">
            <span class="auth-field-index">01</span>
            <input
              id="server-url"
              v-model="form.serverUrl"
              type="url"
              required
              placeholder=" "
              class="auth-input-minimal"
              :disabled="connecting"
              @input="clearStatus"
            />
            <label for="server-url" class="auth-label-floating">服务器地址</label>
          </div>

          <section class="server-shortcuts">
            <div class="server-shortcuts__header">
              <span class="server-shortcuts__title">常用地址</span>
            </div>
            <div class="server-chip-list">
              <button
                v-for="url in quickServerUrls"
                :key="url"
                type="button"
                class="server-chip"
                @click="applyServerUrl(url)"
              >
                {{ url }}
              </button>
            </div>
          </section>

          <section v-if="recentServerUrls.length" class="server-shortcuts">
            <div class="server-shortcuts__header">
              <span class="server-shortcuts__title">最近连接</span>
              <button type="button" class="server-shortcuts__clear" @click="handleClearRecent">
                清空
              </button>
            </div>
            <div class="server-chip-list">
              <button
                v-for="url in recentServerUrls"
                :key="url"
                type="button"
                class="server-chip server-chip--recent"
                @click="applyServerUrl(url)"
              >
                {{ url }}
              </button>
            </div>
          </section>

          <div class="auth-field-minimal">
            <span class="auth-field-index">02</span>
            <button
              type="button"
              class="test-button"
              :disabled="!form.serverUrl.trim() || testing"
              @click="handleTest"
            >
              <span v-if="testing" class="test-spinner"></span>
              <span v-else-if="testResult !== null" :class="['test-status', testResult ? 'test-status--ok' : 'test-status--fail']">
                {{ testResult ? '✓ 连接成功' : '✗ 连接失败' }}
              </span>
              <span v-else>测试连接</span>
            </button>
          </div>

          <div class="connection-feedback" :class="connectionFeedbackClass">
            <span>{{ connectionMessage }}</span>
          </div>

          <Button
            type="submit"
            class="auth-submit-minimal"
            :disabled="connecting || !form.serverUrl.trim()"
          >
            {{ connecting ? '连接中...' : '进入系统' }}
          </Button>

          <div class="auth-footer-minimal">
            <span>本地开发？</span>
            <button type="button" class="auth-link-minimal" @click="fillLocalhost">使用本地地址</button>
          </div>
        </form>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useServerConfig } from '@/composables/useServerConfig'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

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
  form.value.serverUrl = getServerUrl()
})

const currentServerLabel = computed(() => getServerUrl() || '返回登录')

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
    connectionMessage.value = result.message
  } catch {
    testResult.value = false
    connectionMessage.value = '测试失败'
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

const connectionFeedbackClass = computed(() => {
  if (!connectionMessage.value) return ''
  return testResult.value === true ? 'connection-feedback--ok' : 'connection-feedback--fail'
})
</script>

<style scoped src="../styles/views/auth-entry.css"></style>

<style scoped>
.auth-sidebar__desc {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-top: -0.5rem;
}

.auth-sidebar__hint {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 2rem;
}

.server-shortcuts {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: -1.25rem;
}

.server-shortcuts__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.server-shortcuts__title {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.34);
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.server-shortcuts__clear {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.38);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  cursor: pointer;
  transition: color 0.2s ease;
}

.server-shortcuts__clear:hover {
  color: #ff4d00;
}

.server-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.server-chip {
  min-height: 2.4rem;
  padding: 0.55rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.02);
  color: rgba(255, 255, 255, 0.84);
  font-size: 0.78rem;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: border-color 0.25s ease, background-color 0.25s ease, color 0.25s ease;
}

.server-chip:hover {
  border-color: rgba(255, 77, 0, 0.55);
  background: rgba(255, 77, 0, 0.08);
  color: #fff;
}

.server-chip--recent {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.74rem;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.hint-marker {
  font-family: 'Courier New', monospace;
  color: #ff4d00;
  opacity: 0.5;
}

.test-button {
  width: 100%;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.8rem 0;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  text-align: left;
}

.test-button:hover:not(:disabled) {
  border-bottom-color: #ff4d00;
  color: #ff4d00;
}

.test-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.test-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 1px solid rgba(255, 77, 0, 0.3);
  border-top-color: #ff4d00;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.test-status {
  font-size: 0.78rem;
  letter-spacing: 0.15em;
}

.test-status--ok {
  color: #4ade80;
}

.test-status--fail {
  color: #f87171;
}

.connection-feedback {
  margin-top: -1.5rem;
  padding: 0.5rem 0;
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.3);
  min-height: 1.5rem;
  transition: all 0.3s ease;
}

.connection-feedback--ok {
  color: #4ade80;
}

.connection-feedback--fail {
  color: #f87171;
}

@media (max-width: 1024px) {
  .auth-sidebar__hint {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
  }

  .server-chip {
    width: 100%;
    text-align: left;
  }
}
</style>
