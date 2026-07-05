<template>
  <div class="auth-shell auth-shell--enter">
    <div class="auth-shell__layout">
      <div class="auth-shell__atmosphere" aria-hidden="true" />

      <aside class="auth-brand">
        <div class="auth-brand__glow" aria-hidden="true" />

        <div class="auth-brand__inner">
          <div class="auth-brand__top">
            <div class="auth-brand__mark">
              <BrandLogo size="sm" />
              <span class="auth-brand__product">归仓</span>
            </div>
          </div>

          <div class="auth-brand__copy">
            <span class="auth-brand__eyebrow">归仓 / 引擎</span>
            <h1 class="auth-brand__headline">
              把归仓，
              <span class="auth-brand__headline-accent">接到您的引擎。</span>
            </h1>
            <p class="auth-brand__sub">
              归仓的前端只是一扇窗。告诉它您后端引擎的地址，它就会为您拉取所有订阅与媒体。
            </p>

            <ul class="auth-brand__features">
              <li class="auth-brand__feature">
                <AppIcon name="server" class="auth-brand__feature-icon" />
                <span>支持自部署与本地开发</span>
              </li>
              <li class="auth-brand__feature">
                <AppIcon name="shieldCheck" class="auth-brand__feature-icon" />
                <span>连接信息仅保存在本机</span>
              </li>
              <li class="auth-brand__feature">
                <AppIcon name="bolt" class="auth-brand__feature-icon" />
                <span>连上即可立即进入系统</span>
              </li>
            </ul>
          </div>

          <div class="auth-brand__foot">
            <span>归仓 · 个人内容订阅中心</span>
          </div>
        </div>
      </aside>

      <section class="auth-form">
        <div class="auth-form__inner">
          <header class="auth-form__header">
            <h2 class="auth-form__title app-h1">归仓核心配置</h2>
            <p class="auth-form__subtitle">连接至您的后端服务引擎</p>
          </header>

          <form
            novalidate
            class="auth-form__form"
            @submit.prevent="handleConnect"
          >
            <Transition name="auth-alert">
              <Alert v-if="errorMessage" variant="error">
                <AppIcon name="error" class="h-4 w-4" />
                <AlertDescription>{{ errorMessage }}</AlertDescription>
              </Alert>
            </Transition>

            <div class="auth-field">
              <label for="server-url" class="auth-field__label">服务器接口地址</label>
              <div class="auth-field__wrap">
                <AppIcon name="server" class="auth-field__icon" />
                <Input
                  id="server-url"
                  v-model="form.serverUrl"
                  type="url"
                  required
                  placeholder="http://127.0.0.1:8001"
                  :disabled="connecting"
                  class="auth-field__input auth-field__input--with-icon auth-field__input--with-action"
                  @input="clearStatus"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  :disabled="!form.serverUrl.trim() || testing"
                  :loading="testing"
                  class="auth-field__action auth-field__action--wide"
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
                    <button
                      type="button"
                      class="auth-options__chip"
                      @click="applyServerUrl(url)"
                    >
                      <span class="auth-options__chip-text">{{ url }}</span>
                    </button>
                  </li>
                </ul>
              </div>

              <div v-if="recentServerUrls.length" class="auth-options__group">
                <div class="auth-options__head">
                  <span class="auth-options__title">最近连接</span>
                  <button type="button" class="auth-options__clear" @click="handleClearRecent">
                    清空
                  </button>
                </div>
                <ul class="auth-options__list">
                  <li v-for="url in recentServerUrls" :key="url">
                    <button
                      type="button"
                      class="auth-options__chip"
                      :title="url"
                      @click="applyServerUrl(url)"
                    >
                      <span class="auth-options__chip-text">{{ url }}</span>
                    </button>
                  </li>
                </ul>
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              :loading="connecting"
              :disabled="!form.serverUrl.trim()"
              class="auth-form__submit"
            >
              {{ connecting ? '正在连接' : '确认并进入系统' }}
            </Button>
          </form>

          <footer class="auth-form__foot">
            <span class="auth-form__foot-text">本地开发？</span>
            <button
              type="button"
              class="auth-form__foot-link"
              @click="fillLocalhost"
            >
              快速切换至本机地址
            </button>
          </footer>

          <router-link to="/login" class="auth-form__back">
            <AppIcon name="back" class="auth-form__back-icon" />
            返回登录页面
          </router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Logger } from '@/shared/lib/logger'
import AppIcon from '@/shared/icons/AppIcon.vue'
import BrandLogo from '@/shared/components/BrandLogo.vue'
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