<template>
  <div class="auth-shell">
    <!-- Back to Login -->
    <div class="auth-topbar">
      <router-link to="/login" class="auth-topbar__link">
        <span class="auth-topbar__eyebrow">Auth</span>
        <span class="auth-topbar__value">{{ currentServerLabel }}</span>
      </router-link>
    </div>

    <div class="auth-layout">
      <!-- Left Panel: Branding -->
      <aside class="auth-sidebar">
        <h1 class="auth-sidebar__brand">SQRL</h1>
        <p class="auth-sidebar__tagline">
          连接至后端服务器。<br>
          开始使用视频订阅平台。
        </p>
        <div class="auth-sidebar__status">
          服务器配置
        </div>
      </aside>

      <!-- Right Panel: Form -->
      <main class="auth-main">
        <form class="auth-form-unified" @submit.prevent="handleConnect">
          <!-- Header -->
          <div class="auth-form-header">
            <h2 class="auth-form-title">连接服务器</h2>
            <p class="auth-form-subtitle">输入后端服务器地址</p>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="auth-error">
            {{ errorMessage }}
          </div>

          <!-- Server URL Field -->
          <div class="auth-field">
            <label for="server-url" class="auth-field__label">服务器地址</label>
            <input
              id="server-url"
              v-model="form.serverUrl"
              type="url"
              required
              class="auth-input"
              placeholder="http://127.0.0.1:8001"
              :disabled="connecting"
              @input="clearStatus"
            />
          </div>

          <!-- Quick Server Options -->
          <div class="server-shortcuts">
            <span class="server-shortcuts__label">常用地址</span>
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
          </div>

          <!-- Recent Servers -->
          <div v-if="recentServerUrls.length" class="server-shortcuts">
            <div class="server-shortcuts__header">
              <span class="server-shortcuts__label">最近连接</span>
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
          </div>

          <!-- Test Connection -->
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

          <!-- Connection Feedback -->
          <div v-if="connectionMessage" class="connection-feedback" :class="connectionFeedbackClass">
            {{ connectionMessage }}
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            class="auth-submit"
            :disabled="connecting || !form.serverUrl.trim()"
          >
            {{ connecting ? '连接中...' : '进入系统' }}
          </button>

          <!-- Footer Links -->
          <div class="auth-footer">
            <span>本地开发？</span>
            <button type="button" class="auth-link" @click="fillLocalhost">
              使用本地地址
            </button>
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
/* Server shortcuts - unified style */
.server-shortcuts {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.server-shortcuts__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.server-shortcuts__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.server-shortcuts__clear {
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
}

.server-shortcuts__clear:hover {
  color: hsl(var(--primary));
}

.server-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.server-chip {
  height: 2rem;
  padding: 0 var(--space-3);
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.server-chip:hover {
  border-color: hsl(var(--primary) / 0.5);
  background: hsl(var(--primary) / 0.05);
  color: hsl(var(--primary));
}

.server-chip--recent {
  font-family: var(--font-mono);
}

/* Test button - unified style */
.test-button {
  width: 100%;
  height: 2.75rem;
  background: hsl(var(--secondary));
  border: 1px solid hsl(var(--border));
  color: hsl(var(--muted-foreground));
  font-size: var(--font-size-sm);
  font-weight: 500;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
  display: flex;
  align-items: center;
  justify-content: center;
}

.test-button:hover:not(:disabled) {
  border-color: hsl(var(--primary) / 0.5);
  background: hsl(var(--primary) / 0.05);
  color: hsl(var(--primary));
}

.test-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.test-status {
  font-weight: 500;
}

.test-status--ok {
  color: hsl(var(--success));
}

.test-status--fail {
  color: hsl(var(--destructive));
}

.connection-feedback {
  font-size: var(--font-size-xs);
  color: hsl(var(--muted-foreground));
  min-height: var(--space-4);
  transition: color var(--duration-fast) var(--ease-default);
}

.connection-feedback--ok {
  color: hsl(var(--success));
}

.connection-feedback--fail {
  color: hsl(var(--destructive));
}

@media (max-width: 768px) {
  .server-chip {
    width: 100%;
  }
}
</style>
