<template>
  <main class="auth-entry">
    <header class="auth-entry__masthead">
      <div class="auth-entry__brand" aria-label="归仓">
        <BrandMark class="auth-entry__mark" />
        <span class="auth-entry__product">归仓</span>
        <span class="auth-entry__brand-divider" aria-hidden="true" />
        <span class="auth-entry__product-note">个人媒体工作台</span>
      </div>
      <p class="auth-entry__edition">连接自己的服务器</p>
    </header>

    <div class="auth-entry__layout">
      <div class="auth-entry__workspace">
        <aside class="auth-entry__context" aria-label="连接流程">
          <div class="auth-entry__context-head">
            <span class="auth-entry__context-label">连接流程</span>
            <h2 class="auth-entry__context-title">{{ contextTitle }}</h2>
            <p class="auth-entry__context-description">{{ contextDescription }}</p>
          </div>

          <ol class="auth-entry__steps">
            <li
              class="auth-entry__step"
              :class="{
                'is-active': stage === 'server',
                'is-complete': stage === 'account' && hasServer,
              }"
              :aria-current="stage === 'server' ? 'step' : undefined"
            >
              <span class="auth-entry__step-icon" aria-hidden="true">
                <AppIcon :name="stage === 'account' && hasServer ? 'check' : 'server'" />
              </span>
              <span class="auth-entry__step-copy">
                <span class="auth-entry__step-label">服务器</span>
                <code class="auth-entry__step-value" :title="serverHostFull || undefined">
                  {{ serverHostLabel }}
                </code>
              </span>
              <ServerStatusButton v-if="showServerAction" mode="trust" />
            </li>

            <li
              class="auth-entry__step"
              :class="{ 'is-active': stage === 'account' }"
              :aria-current="stage === 'account' ? 'step' : undefined"
            >
              <span class="auth-entry__step-icon" aria-hidden="true">
                <AppIcon name="user" />
              </span>
              <span class="auth-entry__step-copy">
                <span class="auth-entry__step-label">账户</span>
                <span class="auth-entry__step-value">
                  {{ stage === 'account' ? '验证服务器身份' : '连接后继续' }}
                </span>
              </span>
            </li>

            <li class="auth-entry__step">
              <span class="auth-entry__step-icon" aria-hidden="true">
                <AppIcon name="home" />
              </span>
              <span class="auth-entry__step-copy">
                <span class="auth-entry__step-label">工作台</span>
                <span class="auth-entry__step-value">浏览、整理与播放</span>
              </span>
            </li>
          </ol>

          <p class="auth-entry__privacy">
            账户与内容由你指定的服务器保管。
          </p>
        </aside>

        <section class="auth-entry__panel" :aria-labelledby="headingId">
          <header class="auth-entry__intro">
            <h1 :id="headingId" class="auth-entry__title">{{ title }}</h1>
            <p v-if="description" class="auth-entry__description">{{ description }}</p>
          </header>

          <div class="auth-entry__content">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="auth-entry__footer">
            <slot name="footer" />
          </footer>
        </section>
      </div>
    </div>

    <footer class="auth-entry__page-footer">
      <span>归仓桌面端</span>
      <span>本地优先 · 私有部署</span>
    </footer>

    <div v-if="$slots.below" class="auth-entry__below">
      <slot name="below" />
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BrandMark from '@/shared/components/BrandMark.vue'
import ServerStatusButton from '@/shared/components/ServerStatusButton.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { useServerConfig } from '@/shared/composables/useServerConfig'

const props = withDefaults(defineProps<{
  title: string
  description?: string
  showServerAction?: boolean
  stage?: 'server' | 'account'
}>(), {
  description: '',
  showServerAction: true,
  stage: 'account',
})

const headingId = 'auth-entry-heading'
const { serverUrl } = useServerConfig()

const hasServer = computed(() => Boolean(serverUrl.value?.trim()))
const serverHostFull = computed(() => serverUrl.value || '')

const serverHostLabel = computed(() => {
  const url = serverUrl.value
  if (!url) return '尚未配置'
  try {
    return new URL(url).host || url
  } catch {
    return url
  }
})

const contextTitle = computed(() => (
  props.stage === 'server' ? '连接这台客户端' : '进入你的工作台'
))

const contextDescription = computed(() => (
  props.stage === 'server'
    ? '先选择归仓服务端，再使用该服务器上的账户。'
    : '确认服务器与账户后，继续管理自己的媒体内容。'
))
</script>
