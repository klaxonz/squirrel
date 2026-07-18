<template>
  <AuthEntryCard
    title="创建账户"
    description="在此服务器上创建账户。"
  >
    <form class="auth-entry__form" @submit.prevent="handleSubmit">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <div class="auth-field">
        <label for="nickname" class="auth-field__label">昵称</label>
        <Input
          fluid
          id="nickname"
          v-model="form.nickname"
          type="text"
          required
          size="lg"
          :disabled="loading"
          autocomplete="nickname"
          placeholder="怎么称呼你"
          class="auth-field__input"
        />
      </div>

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
            minlength="8"
            size="lg"
            :disabled="loading"
            autocomplete="new-password"
            placeholder="至少 8 位"
            aria-describedby="password-hint"
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
        <span id="password-hint" class="auth-field__hint">至少 8 个字符</span>
      </div>

      <Button type="submit" size="lg" :loading="loading" class="auth-entry__submit">
        {{ loading ? '正在创建…' : '创建账户' }}
      </Button>
    </form>

    <template #footer>
      <span class="auth-entry__footer-text">已有账户？</span>
      <router-link to="/login" class="auth-entry__link">直接登录</router-link>
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
import { Input } from '@/shared/ui/input'
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

const handleSubmit = async () => {
  if (loading.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await userStore.register(form.value)
    if (result.error) {
      errorMessage.value = result.error instanceof Error ? result.error.message : '注册失败'
      return
    }

    await router.push('/login')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
