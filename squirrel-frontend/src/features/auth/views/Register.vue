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
            <span class="auth-brand__eyebrow">归仓 / 加入</span>
            <h1 class="auth-brand__headline">
              建一个属于您的，
              <span class="auth-brand__headline-accent">安静的归处。</span>
            </h1>
            <p class="auth-brand__sub">
              把分散在各处的订阅、频道与播放列表聚合起来。一切只为您一个人。
            </p>

            <ul class="auth-brand__features">
              <li class="auth-brand__feature">
                <AppIcon name="shieldCheck" class="auth-brand__feature-icon" />
                <span>账号数据仅归属您本人</span>
              </li>
              <li class="auth-brand__feature">
                <AppIcon name="inbox" class="auth-brand__feature-icon" />
                <span>未读内容自动汇总</span>
              </li>
              <li class="auth-brand__feature">
                <AppIcon name="playback" class="auth-brand__feature-icon" />
                <span>跨端继续上次播放</span>
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
            <h2 class="auth-form__title app-h1">加入归仓</h2>
            <p class="auth-form__subtitle">创建账户，开始管理您的内容订阅</p>
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
              <label for="nickname" class="auth-field__label">昵称</label>
              <div class="auth-field__wrap">
                <AppIcon name="user" class="auth-field__icon" />
                <Input
                  id="nickname"
                  v-model="form.nickname"
                  type="text"
                  required
                  placeholder="您希望被称呼的名字"
                  autocomplete="nickname"
                  class="auth-field__input auth-field__input--with-icon"
                />
              </div>
            </div>

            <div class="auth-field">
              <label for="email" class="auth-field__label">邮箱</label>
              <div class="auth-field__wrap">
                <AppIcon name="info" class="auth-field__icon" />
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
                <span class="auth-field__hint">至少 8 位字符</span>
              </div>
              <div class="auth-field__wrap">
                <AppIcon name="security" class="auth-field__icon" />
                <Input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  minlength="8"
                  placeholder="设置一个安全的密码"
                  autocomplete="new-password"
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

            <Button
              type="submit"
              size="lg"
              :loading="loading"
              class="auth-form__submit"
            >
              {{ loading ? '正在注册' : '创建账户' }}
            </Button>
          </form>

          <footer class="auth-form__foot">
            <span class="auth-form__foot-text">已有账户？</span>
            <router-link to="/login" class="auth-form__foot-link">直接登录</router-link>
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

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const showPassword = ref(false)
const errorMessage = ref('')
const form = ref({
  nickname: '',
  email: '',
  password: '',
})

// ponytail: the user store catches the thrown ApiError and re-shapes it into a
// { data, error } tuple, so this form can render the message inline (not via the
// global mutation toast).
const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  const result = await userStore.register(form.value)
  loading.value = false
  if (result.error) {
    errorMessage.value = result.error instanceof Error ? result.error.message : '注册失败'
    return
  }

  await router.push('/login')
}
</script>