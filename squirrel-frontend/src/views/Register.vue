<template>
  <div class="auth-shell auth-shell--register">
    <div class="auth-shell__glow auth-shell__glow--primary"></div>
    <div class="auth-shell__glow auth-shell__glow--secondary"></div>

    <div class="auth-layout">
      <section class="auth-hero">
        <div class="auth-badge">Curated Video Workspace</div>
        <img src="/squirrel-icon.png" class="auth-logo" alt="Logo">
        <h1 class="auth-title">建立属于你的内容台。</h1>
        <p class="auth-copy">
          从第一条订阅开始，把多站点视频、观看习惯和同步任务收进一个更安静、更稳定的界面里。
        </p>

        <div class="auth-metrics">
          <div class="auth-metric">
            <span class="auth-metric__label">统一来源</span>
            <span class="auth-metric__value">追踪多个站点，不再分散切换。</span>
          </div>
          <div class="auth-metric">
            <span class="auth-metric__label">主题跟随</span>
            <span class="auth-metric__value">浅色、深色和系统模式一键切换。</span>
          </div>
          <div class="auth-metric">
            <span class="auth-metric__label">观看上下文</span>
            <span class="auth-metric__value">保留进度、交互和推荐链路。</span>
          </div>
        </div>
      </section>

      <Card class="auth-panel">
        <div class="auth-panel__header">
          <p class="auth-panel__eyebrow">Create account</p>
          <h2 class="auth-panel__title">创建新账号</h2>
          <p class="auth-panel__desc">初始化你的订阅空间和播放器偏好。</p>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <Alert v-if="errorMessage" variant="destructive">
            <AlertDescription>{{ errorMessage }}</AlertDescription>
          </Alert>

          <div class="auth-field">
            <Label for="nickname" class="auth-label">昵称</Label>
            <Input
              id="nickname"
              v-model="form.nickname"
              type="text"
              required
              placeholder="给自己起个名字"
            />
          </div>

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
              placeholder="设置密码"
            />
          </div>

          <Button type="submit" size="lg" class="auth-submit w-full" :disabled="loading">
            <span v-if="loading">注册中...</span>
            <span v-else>创建账号</span>
          </Button>

          <div class="auth-panel__footer">
            <span class="text-muted-foreground">已有账号？</span>
            <router-link to="/login" class="auth-link">立即登录</router-link>
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
const { register } = useUser()
const loading = ref(false)
const errorMessage = ref('')
const form = ref({
  nickname: '',
  email: '',
  password: '',
})

const getErrorMessage = (error) => {
  if (!error) return '注册失败，请稍后再试。'
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string') return error.message
  if (typeof error?.detail === 'string') return error.detail
  if (typeof error?.response?.data?.detail === 'string') return error.response.data.detail
  return '注册失败，请检查输入内容后重试。'
}

const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const result = await register(form.value)
    if (result.error) {
      errorMessage.value = getErrorMessage(result.error)
      return
    }

    await router.push('/login')
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="../styles/views/auth-entry.css"></style>
