<template>
  <div class="auth-shell">
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

      <section class="auth-panel">
        <div class="auth-panel__header">
          <p class="auth-panel__eyebrow">Create account</p>
          <h2 class="auth-panel__title">创建新账号</h2>
          <p class="auth-panel__desc">初始化你的订阅空间和播放器偏好。</p>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="auth-field">
            <label for="nickname" class="auth-label">昵称</label>
            <input
              id="nickname"
              v-model="form.nickname"
              type="text"
              required
              class="auth-input"
              placeholder="给自己起个名字"
            >
          </div>
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
              placeholder="设置密码"
            >
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="auth-submit"
          >
            <span v-if="loading">注册中...</span>
            <span v-else>创建账号</span>
          </button>

          <div class="auth-panel__footer">
            <span class="text-muted-foreground">已有账号？</span>
            <router-link
              to="/login"
              class="auth-link"
            >
              立即登录
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
const { register } = useUser();
const loading = ref(false);
const form = ref({
  nickname: '',
  email: '',
  password: ''
});

const handleSubmit = async () => {
  loading.value = true;
  try {
    const result = await register(form.value)
    if (result.error) {
      throw result.error
    }
    router.push('/login');
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
  filter: blur(74px);
  opacity: 0.54;
  pointer-events: none;
}

.auth-shell__glow--primary {
  top: -5rem;
  right: -2rem;
  width: 18rem;
  height: 18rem;
  background: radial-gradient(circle, rgba(209, 138, 77, 0.28), transparent 70%);
}

.auth-shell__glow--secondary {
  left: -5rem;
  bottom: -4rem;
  width: 21rem;
  height: 21rem;
  background: radial-gradient(circle, rgba(81, 108, 132, 0.2), transparent 72%);
}

.auth-layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(18rem, 28rem);
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
    linear-gradient(160deg, hsl(var(--card) / 0.98), hsl(var(--secondary) / 0.82));
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
