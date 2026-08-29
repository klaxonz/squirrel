<template>
  <AuthEntryCard
    title="加入归仓"
    description="在当前服务器创建账户，开始同步多站内容。"
  >
    <form class="auth-entry__form" @submit.prevent="handleSubmit">
      <Transition name="auth-alert">
        <Alert v-if="errorMessage" variant="error">
          <AppIcon name="error" class="h-4 w-4" />
          <p class="text-sm [&_p]:leading-relaxed">{{ errorMessage }}</p>
        </Alert>
      </Transition>

      <AppFormField id="nickname" label="昵称" required class="auth-field">
        <template #default="{ control }">
          <Input
            v-bind="control"
            fluid
            v-model="form.nickname"
            type="text"
            size="lg"
            :disabled="loading"
            autocomplete="nickname"
            placeholder="怎么称呼你"
            class="auth-field__input"
          />
        </template>
      </AppFormField>

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

      <AppFormField
        id="password"
        label="密码"
        description="至少 8 个字符"
        required
        class="auth-field"
      >
        <template #default="{ control }">
          <div class="auth-field__wrap">
            <Input
              v-bind="control"
              fluid
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              minlength="8"
              size="lg"
              :disabled="loading"
              autocomplete="new-password"
              placeholder="至少 8 位"
              class="auth-field__input auth-field__input--with-action"
            />
            <Button
              type="button"
             
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
import AppFormField from '@/shared/components/layout/AppFormField.vue'
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
