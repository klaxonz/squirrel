<template>
  <div class="auth-shell">
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
            <span class="auth-metric__value">统一追踪站点与更新</span>
          </div>
          <div class="auth-metric">
            <span class="auth-metric__label">播放器</span>
            <span class="auth-metric__value">沉浸式浅深双主题</span>
          </div>
          <div class="auth-metric">
            <span class="auth-metric__label">同步中心</span>
            <span class="auth-metric__value">把刷新和修复变成可见流程</span>
          </div>
        </div>
      </section>

      <section class="auth-panel">
        <div class="auth-panel__header">
          <p class="auth-panel__eyebrow">Welcome back</p>
          <h2 class="auth-panel__title">登录到 Squirrel</h2>
          <p class="auth-panel__desc">继续你的订阅、历史记录和播放器偏好。</p>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="auth-field">
            <label for="email" class="auth-label">邮箱</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              class="auth-input"
              placeholder="name@example.com"
            >
          </div>
          <div class="auth-field">
            <label for="password" class="auth-label">密码</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              class="auth-input"
              placeholder="输入密码"
            >
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="auth-submit"
          >
            <span v-if="loading">登录中...</span>
            <span v-else>进入工作台</span>
          </button>

          <div class="auth-panel__footer">
            <span class="text-muted-foreground">还没有账号？</span>
            <router-link
              to="/register"
              class="auth-link"
            >
              立即注册
            </router-link>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUser } from '../composables/useUser';

const router = useRouter();
const { login } = useUser();
const loading = ref(false);
const form = ref({
  email: '',
  password: ''
});

const handleSubmit = async () => {
  loading.value = true;
  try {
    const result = await login(form.value)
    if (!result.error) {
      await router.push('/')
    }
  } catch (error) {
    // Error handling without toast
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.auth-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1.25rem, 2vw, 2rem);
}

.auth-shell__glow {
  position: absolute;
  border-radius: 9999px;
  filter: blur(70px);
  opacity: 0.55;
  pointer-events: none;
}

.auth-shell__glow--primary {
  top: -6rem;
  left: -3rem;
  width: 18rem;
  height: 18rem;
  background: radial-gradient(circle, rgba(209, 138, 77, 0.3), transparent 70%);
}

.auth-shell__glow--secondary {
  right: -4rem;
  bottom: -5rem;
  width: 20rem;
  height: 20rem;
  background: radial-gradient(circle, rgba(81, 108, 132, 0.2), transparent 72%);
}

.auth-layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(18rem, 28rem);
  gap: clamp(1rem, 2vw, 2rem);
  width: min(100%, 72rem);
  align-items: stretch;
}

.auth-hero,
.auth-panel {
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1.75rem;
  backdrop-filter: blur(18px);
}

.auth-hero {
  padding: clamp(1.5rem, 3vw, 3rem);
  background:
    linear-gradient(150deg, hsl(var(--card) / 0.98), hsl(var(--secondary) / 0.84));
  box-shadow: 0 32px 80px hsl(var(--surface-shadow));
}

.auth-panel {
  padding: clamp(1.25rem, 2.5vw, 2rem);
  background: hsl(var(--card) / 0.94);
  box-shadow: 0 22px 56px hsl(var(--surface-shadow));
}

.auth-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  padding: 0.45rem 0.8rem;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.12);
}

.auth-logo {
  width: 4.5rem;
  height: 4.5rem;
  margin-top: 2rem;
  border-radius: 1.5rem;
  box-shadow: 0 22px 44px hsl(var(--surface-shadow));
}

.auth-title {
  margin-top: 1.5rem;
  font-size: clamp(2rem, 4vw, 3.7rem);
  line-height: 0.98;
  font-weight: 700;
  color: hsl(var(--foreground));
  max-width: 10ch;
}

.auth-copy {
  margin-top: 1rem;
  max-width: 34rem;
  font-size: 0.96rem;
  line-height: 1.7;
  color: hsl(var(--muted-foreground));
}

.auth-metrics {
  margin-top: 2rem;
  display: grid;
  gap: 0.9rem;
}

.auth-metric {
  display: grid;
  gap: 0.18rem;
  padding: 1rem 1.1rem;
  border-radius: 1.15rem;
  background: hsl(var(--background) / 0.54);
  border: 1px solid hsl(var(--border) / 0.7);
}

.auth-metric__label {
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.auth-metric__value {
  font-size: 0.96rem;
  color: hsl(var(--foreground));
}

.auth-panel__header {
  margin-bottom: 1.75rem;
}

.auth-panel__eyebrow {
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.auth-panel__title {
  margin-top: 0.6rem;
  font-size: 1.9rem;
  line-height: 1.1;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.auth-panel__desc {
  margin-top: 0.65rem;
  font-size: 0.9rem;
  line-height: 1.65;
  color: hsl(var(--muted-foreground));
}

.auth-form {
  display: grid;
  gap: 1rem;
}

.auth-field {
  display: grid;
  gap: 0.45rem;
}

.auth-label {
  font-size: 0.78rem;
  color: hsl(var(--muted-foreground));
}

.auth-input {
  appearance: none;
  width: 100%;
  min-height: 3rem;
  border-radius: 1rem;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background) / 0.78);
  padding: 0.85rem 1rem;
  font-size: 0.92rem;
  color: hsl(var(--foreground));
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.auth-input::placeholder {
  color: hsl(var(--muted-foreground));
}

.auth-input:focus-visible {
  outline: none;
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 4px hsl(var(--ring) / 0.14);
}

.auth-submit {
  min-height: 3.25rem;
  border: 0;
  border-radius: 9999px;
  background: linear-gradient(135deg, hsl(var(--primary)), color-mix(in srgb, hsl(var(--primary)) 72%, hsl(var(--foreground))));
  color: hsl(var(--primary-foreground));
  font-size: 0.94rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 18px 40px hsl(var(--surface-shadow));
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.auth-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 22px 46px hsl(var(--surface-shadow));
}

.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-panel__footer {
  display: flex;
  gap: 0.35rem;
  justify-content: center;
  font-size: 0.88rem;
}

.auth-link {
  color: hsl(var(--foreground));
  font-weight: 600;
  transition: color 0.2s ease;
}

.auth-link:hover {
  color: hsl(var(--primary));
}

@media (max-width: 960px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }

  .auth-title {
    max-width: none;
  }
}

@media (max-width: 640px) {
  .auth-shell {
    padding: 0.75rem;
  }

  .auth-hero,
  .auth-panel {
    border-radius: 1.4rem;
  }

  .auth-hero {
    padding: 1.25rem;
  }

  .auth-panel {
    padding: 1.1rem;
  }

  .auth-logo {
    width: 3.75rem;
    height: 3.75rem;
    margin-top: 1.25rem;
  }
}
</style>
