<template>
  <main class="auth-entry">
    <header class="auth-entry__masthead">
      <div class="auth-entry__brand" aria-label="归仓">
        <BrandMark class="auth-entry__mark" />
        <div class="auth-entry__brand-copy">
          <span class="auth-entry__product">归仓</span>
          <span class="auth-entry__product-en">SQUIRREL</span>
        </div>
      </div>

      <p class="auth-entry__edition">
        <span>桌面客户端</span>
        <span aria-hidden="true">/</span>
        <span>私有部署</span>
      </p>
    </header>

    <div class="auth-entry__layout">
      <section class="auth-entry__manifest" aria-label="产品简介">
        <div class="auth-entry__manifest-copy">
          <p class="auth-entry__kicker">订阅 · 整理 · 播放</p>
          <h2 class="auth-entry__statement">
            把散落的内容，<br>
            <span>收回一处。</span>
          </h2>
          <p class="auth-entry__summary">
            订阅、同步、检索与播放。<br>
            内容留在你的服务器，秩序留给你自己。
          </p>
        </div>

        <dl class="auth-entry__index">
          <div>
            <dt>01</dt>
            <dd>视频订阅</dd>
          </div>
          <div>
            <dt>02</dt>
            <dd>RSS 归集</dd>
          </div>
          <div>
            <dt>03</dt>
            <dd>音乐与播放</dd>
          </div>
        </dl>
      </section>

      <section class="auth-entry__panel" :aria-labelledby="headingId">
        <div class="auth-entry__panel-head" aria-hidden="true">
          <span>账户验证</span>
          <span>01 / 01</span>
        </div>

        <header class="auth-entry__intro">
          <p v-if="eyebrow" class="auth-entry__eyebrow">{{ eyebrow }}</p>
          <h1 :id="headingId" class="auth-entry__title">{{ title }}</h1>
          <p v-if="description" class="auth-entry__description">{{ description }}</p>
        </header>

        <div
          class="auth-entry__server"
          :aria-label="`当前服务器：${serverHostLabel}，${statusLabel}`"
        >
          <span class="auth-entry__server-index" aria-hidden="true">↳</span>
          <div class="auth-entry__server-copy">
            <span class="auth-entry__server-label">当前服务器</span>
            <code class="auth-entry__server-host" :title="serverHostFull || undefined">
              {{ serverHostLabel }}
            </code>
          </div>
          <span class="auth-entry__status">{{ statusLabel }}</span>
          <ServerStatusButton v-if="showServerAction" mode="trust" />
        </div>

        <div class="auth-entry__content">
          <slot />
        </div>

        <footer v-if="$slots.footer" class="auth-entry__footer">
          <slot name="footer" />
        </footer>
      </section>
    </div>

    <footer class="auth-entry__page-footer" aria-hidden="true">
      <span>数据留在自己的服务器</span>
      <span>本地优先</span>
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
import { useServerConfig } from '@/shared/composables/useServerConfig'

withDefaults(defineProps<{
  title: string
  description?: string
  eyebrow?: string
  showServerAction?: boolean
}>(), {
  description: '',
  eyebrow: '',
  showServerAction: true,
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

// A stored address is configuration, not evidence that the server is healthy.
const statusLabel = computed(() => (hasServer.value ? '地址已保存' : '等待连接'))
</script>
