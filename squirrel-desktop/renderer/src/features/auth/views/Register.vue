<template>
  <AuthEntryCard title="加入归仓" description="创建账户，开始管理您的内容订阅">
    <form novalidate class="auth-entry__form" @submit.prevent="handleSubmit">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <div class="auth-field">
        <label for="nickname" class="auth-field__label">昵称</label>
        <Input fluid
          id="nickname"
          v-model="form.nickname"
          type="text"
          required
          placeholder="您希望被称呼的名字"
          autocomplete="nickname"
          class="auth-field__input"
        />
      </div>

      <div class="auth-field">
        <label for="email" class="auth-field__label">邮箱</label>
        <Input fluid
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
        <div class="auth-field__row">
          <label for="password" class="auth-field__label">密码</label>
          <span class="auth-field__hint">至少 8 位字符</span>
        </div>
        <div class="auth-field__wrap">
          <Input fluid
            id="password"
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            required
            minlength="8"
            placeholder="设置一个安全的密码"
            autocomplete="new-password"
            class="auth-field__input auth-field__input--with-action"
          />
          <Button
            type="button"
            text severity="secondary"
            size="sm" icon-only
            class="auth-field__action"
            :title="showPassword ? '隐藏密码' : '显示密码'"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            @click="showPassword = !showPassword"
          >
            <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Button type="submit" size="lg" :loading="loading" class="auth-entry__submit">
        {{ loading ? '正在注册' : '创建账户' }}
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
