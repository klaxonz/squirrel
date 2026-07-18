<template>
  <AuthEntryCard title="欢迎回来" description="登录您的账户以继续使用归仓">
    <form novalidate class="auth-entry__form" @submit.prevent="handleSubmit">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <AlertDescription>{{ errorMessage }}</AlertDescription>
        </Alert>
      </Transition>

      <div class="auth-field">
        <label for="email" class="auth-field__label">邮箱</label>
        <Input
          id="email"
          v-model="form.email"
          type="email"
          required
          placeholder="name@example.com"
          autocomplete="email"
          class="auth-field__input"
        />
      </div>

      <div class="auth-field">
        <label for="password" class="auth-field__label">密码</label>
        <div class="auth-field__wrap">
          <Input
            id="password"
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            required
            placeholder="请输入密码"
            autocomplete="current-password"
            class="auth-field__input auth-field__input--with-action"
          />
          <Button
            type="button"
            variant="ghost"
            size="mini-icon"
            class="auth-field__action"
            :title="showPassword ? '隐藏密码' : '显示密码'"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            @click="showPassword = !showPassword"
          >
            <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
          </Button>
        </div>
      </div>

      <label for="rememberMe" class="auth-checkbox">
        <Checkbox id="rememberMe" v-model="form.rememberMe" />
        <span>保持登录状态</span>
      </label>

      <Button type="submit" size="lg" :loading="loading" class="auth-entry__submit">
        {{ loading ? '正在登录' : '登录' }}
      </Button>
    </form>

    <template #footer>
      <span class="auth-entry__footer-text">还没有账户？</span>
      <router-link to="/register" class="auth-entry__link">创建新账户</router-link>
    </template>
  </AuthEntryCard>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthEntryCard from '@/features/auth/components/AuthEntryCard.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Alert, AlertDescription } from '@/shared/ui/alert'
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

  resetNavigationHistory()
  await router.push('/')
}
</script>
