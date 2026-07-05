<template>
  <div class="auth-shell auth-shell--enter">
    <div class="auth-shell__layout">
      <!-- Ambient atmosphere that bleeds across the split -->
      <div class="auth-shell__atmosphere" aria-hidden="true" />

      <!-- Brand / editorial panel -->
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
            <span class="auth-brand__eyebrow">归仓 · 内容归处</span>
            <h1 class="auth-brand__headline">
              把您订阅的一切，
              <span class="auth-brand__headline-accent">归于一处。</span>
            </h1>
            <p class="auth-brand__sub">
              RSS 源、YouTube 频道、播客与音乐。把您关心的内容，聚合在一个安静、专注的归处。
            </p>

            <ul class="auth-brand__features">
              <li class="auth-brand__feature">
                <AppIcon name="rss" class="auth-brand__feature-icon" />
                <span>RSS 源、频道与播客</span>
              </li>
              <li class="auth-brand__feature">
                <AppIcon name="playback" class="auth-brand__feature-icon" />
                <span>视频与音乐一站播放</span>
              </li>
              <li class="auth-brand__feature">
                <AppIcon name="shieldCheck" class="auth-brand__feature-icon" />
                <span>本地优先、隐私友好</span>
              </li>
            </ul>
          </div>

          <div class="auth-brand__foot">
            <span>归仓 · 个人内容订阅中心</span>
          </div>
        </div>
      </aside>

      <!-- Form panel -->
      <section class="auth-form">
        <div class="auth-form__inner">
          <header class="auth-form__header">
            <h2 class="auth-form__title app-h1">欢迎回来</h2>
            <p class="auth-form__subtitle">登录您的账户以继续使用归仓</p>
          </header>

          <form
            novalidate
            class="auth-form__form"
            @submit.prevent="handleSubmit"
          >
            <Transition name="auth-alert">
              <Alert v-if="errorMessage" variant="error">
                <AppIcon name="error" class="h-4 w-4" />
                <AlertDescription>{{ errorMessage }}</AlertDescription>
              </Alert>
            </Transition>

            <div class="auth-field">
              <label for="email" class="auth-field__label">邮箱</label>
              <div class="auth-field__wrap">
                <AppIcon name="user" class="auth-field__icon" />
                <Input
                  id="email"
                  v-model="form.email"
                  type="email"
                  required
                  placeholder="name@example.com"
                  autocomplete="email"
                  class="auth-field__input auth-field__input--with-icon"
                />
              </div>
            </div>

            <div class="auth-field">
              <div class="auth-field__row">
                <label for="password" class="auth-field__label">密码</label>
              </div>
              <div class="auth-field__wrap">
                <AppIcon name="security" class="auth-field__icon" />
                <Input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="请输入密码"
                  autocomplete="current-password"
                  class="auth-field__input auth-field__input--with-icon auth-field__input--with-action"
                />
                <button
                  type="button"
                  class="auth-field__action"
                  :title="showPassword ? '隐藏密码' : '显示密码'"
                  :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                  @click="showPassword = !showPassword"
                >
                  <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
                </button>
              </div>
            </div>

            <label for="rememberMe" class="auth-checkbox">
              <input
                id="rememberMe"
                v-model="form.rememberMe"
                type="checkbox"
                class="auth-checkbox__native"
              >
              <span class="auth-checkbox__visual" aria-hidden="true">
                <AppIcon v-if="form.rememberMe" name="check" class="auth-checkbox__check" />
              </span>
              <span class="auth-checkbox__label">保持登录状态</span>
            </label>

            <Button
              type="submit"
              size="lg"
              :loading="loading"
              class="auth-form__submit"
            >
              {{ loading ? '正在登录' : '登录' }}
            </Button>
          </form>

          <footer class="auth-form__foot">
            <span class="auth-form__foot-text">还没有账户？</span>
            <router-link to="/register" class="auth-form__foot-link">创建新账户</router-link>
          </footer>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import BrandLogo from '@/shared/components/BrandLogo.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Alert, AlertDescription } from '@/shared/ui/alert'
import { useUserStore } from '@/shared/stores/user'
import { resetReactive as resetNavigationHistory } from '@/shared/lib/navigationHistory'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const showPassword = ref(false)
const errorMessage = ref('')
const form = ref({
  email: '',
  password: '',
  rememberMe: false,
})

// ponytail: the user store catches the thrown ApiError and re-shapes it into a
// { data, error } tuple, so this form can render the message inline (not via the
// global mutation toast).
const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  const result = await userStore.login({
    email: form.value.email,
    password: form.value.password,
    remember_me: form.value.rememberMe,
  })
  loading.value = false
  if (result.error) {
    errorMessage.value = result.error instanceof Error ? result.error.message : '登录失败'
    return
  }

  // 登录后丢弃登录前累积的所有导航历史，避免「我刚才看了哪些页面」泄漏给
  // 下一次会话。
  resetNavigationHistory()
  await router.push('/')
}
</script>