<template>
  <AuthEntryCard
    title="登录"
    description="使用此服务器上的账户进入工作台。"
  >
    <form class="auth-entry__form" @submit.prevent="handleSubmit">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <div class="auth-field">
        <label for="email" class="auth-field__label">邮箱</label>
        <Input
          fluid
          id="email"
          v-model="form.email"
          type="email"
          required
          size="lg"
          :disabled="loading"
          autocomplete="email"
          placeholder="you@example.com"
          class="auth-field__input"
        />
      </div>

      <div class="auth-field">
        <label for="password" class="auth-field__label">密码</label>
        <div class="auth-field__wrap">
          <Input
            fluid
            id="password"
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            required
            size="lg"
            :disabled="loading"
            autocomplete="current-password"
            placeholder="输入密码"
            class="auth-field__input auth-field__input--with-action"
          />
          <Button
            type="button"
            text
            severity="secondary"
            size="sm"
            icon-only
            class="auth-field__action"
            :disabled="loading"
            :title="showPassword ? '隐藏密码' : '显示密码'"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            @click="showPassword = !showPassword"
          >
            <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
          </Button>
        </div>
      </div>

      <label class="auth-checkbox" for="rememberMe">
        <Checkbox binary id="rememberMe" v-model="form.rememberMe" :disabled="loading" />
        <span>记住我</span>
      </label>

      <Button type="submit" size="lg" :loading="loading" class="auth-entry__submit">
        {{ loading ? '正在登录…' : '登录' }}
      </Button>
    </form>

    <template #footer>
      <span class="auth-entry__footer-text">还没有账户？</span>
      <router-link to="/register" class="auth-entry__link">创建账户</router-link>
    </template>
  </AuthEntryCard>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthEntryCard from '@/features/auth/components/AuthEntryCard.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'
import { Input } from '@/shared/ui/input'
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

const handleSubmit = async () => {
  if (loading.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await userStore.login({
      email: form.value.email,
      password: form.value.password,
      remember_me: form.value.rememberMe,
    })
    if (result.error) {
      errorMessage.value = result.error instanceof Error ? result.error.message : '登录失败'
      return
    }

    resetNavigationHistory()
    await router.push('/')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
