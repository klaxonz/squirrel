<template>
  <div class="auth-shell auth-shell--login">
    <div class="auth-shell__glow auth-shell__glow--primary"></div>
    <div class="auth-shell__glow auth-shell__glow--secondary"></div>

    <div class="auth-layout">
      <section class="auth-hero">
        <div class="auth-badge">Cinematic Feed Reader</div>
        <img src="/squirrel-icon.png" class="auth-logo" alt="Logo">
        <h1 class="auth-title">登录后继续你的观看流。</h1>
        <p class="auth-copy">
          把订阅、播放记录和同步状态放在同一条内容工作流里，少一点后台味，多一点内容质感。
        </p>

        <div class="auth-metrics">
          <div class="auth-metric">
            <span class="auth-metric__label">订阅面板</span>
            <span class="auth-metric__value">统一追踪站点与更新。</span>
          </div>
          <div class="auth-metric">
            <span class="auth-metric__label">播放器</span>
            <span class="auth-metric__value">沉浸式浅深双主题。</span>
          </div>
          <div class="auth-metric">
            <span class="auth-metric__label">同步中心</span>
            <span class="auth-metric__value">把刷新和修复变成可见流程。</span>
          </div>
        </div>
      </section>

      <Card class="auth-panel">
        <div class="auth-panel__header">
          <p class="auth-panel__eyebrow">Welcome back</p>
          <h2 class="auth-panel__title">登录到 Squirrel</h2>
          <p class="auth-panel__desc">继续你的订阅、历史记录和播放器偏好。</p>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <Alert v-if="errorMessage" variant="destructive">
            <AlertDescription>{{ errorMessage }}</AlertDescription>
          </Alert>

          <div class="auth-field">
            <Label for="email" class="auth-label">邮箱</Label>
            <Input
              id="email"
              v-model="form.email"
              type="email"
              required
              placeholder="name@example.com"
            />
          </div>

          <div class="auth-field">
            <Label for="password" class="auth-label">密码</Label>
            <Input
              id="password"
              v-model="form.password"
              type="password"
              required
              placeholder="输入密码"
            />
          </div>

          <Button type="submit" size="lg" class="auth-submit w-full" :disabled="loading">
            <span v-if="loading">登录中...</span>
            <span v-else>进入工作台</span>
          </Button>

          <div class="auth-panel__footer">
            <span class="text-muted-foreground">还没有账号？</span>
            <router-link to="/register" class="auth-link">立即注册</router-link>
          </div>
        </form>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '../composables/useUser'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const router = useRouter()
const { login } = useUser()
const loading = ref(false)
const errorMessage = ref('')
const form = ref({
  email: '',
  password: '',
})

const getErrorMessage = (error) => {
  if (!error) return '登录失败，请稍后再试。'
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string') return error.message
  if (typeof error?.detail === 'string') return error.detail
  if (typeof error?.response?.data?.detail === 'string') return error.response.data.detail
  return '登录失败，请检查邮箱和密码后重试。'
}

const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const result = await login(form.value)
    if (result.error) {
      errorMessage.value = getErrorMessage(result.error)
      return
    }

    await router.push('/')
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="../styles/views/auth-entry.css"></style>
