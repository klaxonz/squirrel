<template>
  <main class="auth-entry">
    <header class="auth-entry__brand" aria-label="归仓">
      <BrandMark class="auth-entry__mark" />
      <span class="auth-entry__product">归仓</span>
    </header>

    <section class="auth-entry__panel" :aria-labelledby="headingId">
      <header class="auth-entry__intro">
        <h1 :id="headingId" class="auth-entry__title">{{ title }}</h1>
        <p v-if="description" class="auth-entry__description">{{ description }}</p>
      </header>

      <div
        v-if="stage === 'account'"
        class="auth-entry__server"
        aria-label="当前服务器"
      >
        <div class="auth-entry__server-copy">
          <span class="auth-entry__server-label">服务器</span>
          <code
            class="auth-entry__server-host"
            :class="{ 'is-empty': !hasServer }"
            :title="serverHostFull || undefined"
          >
            {{ serverHostLabel }}
          </code>
        </div>
        <ServerStatusButton v-if="showServerAction" mode="trust" />
      </div>

      <div class="auth-entry__content">
        <slot />
      </div>

      <footer v-if="$slots.footer" class="auth-entry__footer">
        <slot name="footer" />
      </footer>
    </section>

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
</script>
