<template>
  <AuthEntryCard
    title="登录归仓"
    description="连接到你的自托管订阅中枢，浏览、整理并播放。"
  >
    <form class="auth-entry__form" @submit.prevent="handleSubmit">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <AppFormField id="email" label="邮箱" required class="auth-field">
        <template #default="{ control }">
          <Input
            v-bind="control"
            fluid
            v-model="form.email"
            type="email"
            size="lg"
            :disabled="loading"
            autocomplete="email"
            placeholder="you@example.com"
            class="auth-field__input"
          />
        </template>
      </AppFormField>

      <AppFormField id="password" label="密码" required class="auth-field">
        <template #default="{ control }">
          <div class="auth-field__wrap">
            <Input
              v-bind="control"
              fluid
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              size="lg"
              :disabled="loading"
              autocomplete="current-password"
              placeholder="输入密码"
              class="auth-field__input auth-field__input--with-action"
            />
            <Button
              type="button"
              text
              variant="secondary"
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
        </template>
      </AppFormField>

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
import AppFormField from '@/shared/components/layout/AppFormField.vue'
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
