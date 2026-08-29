<template>
  <PopoverRoot v-model:open="popoverOpen">
    <PopoverTrigger as-child>
    <Button
      type="button"
     
      variant="secondary"
      :icon-only="mode === 'floating'"
      :class="[
        'server-status-trigger',
        {
          'server-status-trigger--open': popoverOpen,
          'server-status-trigger--trust': mode === 'trust',
        },
      ]"
      :title="currentServerLabel"
      :aria-label="triggerAriaLabel"
    >
      <AppIcon name="server" class="server-status-trigger__icon" />
      <span v-if="mode !== 'floating'" class="server-status-trigger__label">
        {{ actionLabel }}
      </span>
    </Button>
    </PopoverTrigger>

    <PopoverContent
      :class="[
        'server-status-popover',
        { 'server-status-popover--trust': mode === 'trust' },
      ]"
    >
      <header class="server-status-popover__head">
        <span class="server-status-popover__eyebrow">服务器</span>
        <span
          class="server-status-popover__state"
          :class="hasFreshSuccess
            ? 'server-status-popover__state--ok'
            : 'server-status-popover__state--idle'"
        >
          <span class="server-status-popover__state-dot" />
          {{ connectionStateLabel }}
        </span>
      </header>

      <div class="server-status-popover__url">
        <span class="server-status-popover__url-label">当前地址</span>
        <code class="server-status-popover__url-value">{{ currentServerLabel }}</code>
      </div>

      <div class="server-status-popover__actions">
        <Button
          type="button"
         
          variant="outline"
          size="sm"
          class="server-status-popover__action"
          :disabled="!currentServerUrl || testing"
          :loading="testing"
          @click="handleTest"
        >
          <AppIcon v-if="!testing" name="bolt" class="server-status-popover__action-icon" />
          <span>{{ testing ? '测试中' : '测试连接' }}</span>
        </Button>

        <Button
          type="button"
         
          variant="outline"
          size="sm"
          class="server-status-popover__action"
          @click="goToServerConfig"
        >
          <AppIcon name="settingsPanel" class="server-status-popover__action-icon" />
          <span>{{ currentServerUrl ? '更换地址' : '去配置' }}</span>
        </Button>
      </div>

      <p
        v-if="testResult === 'ok'"
        class="server-status-popover__feedback server-status-popover__feedback--ok"
      >
        <AppIcon name="statusSuccess" class="server-status-popover__feedback-icon" />
        连接正常
      </p>
      <p
        v-else-if="testResult === 'fail'"
        class="server-status-popover__feedback server-status-popover__feedback--err"
      >
        <AppIcon name="warning" class="server-status-popover__feedback-icon" />
        {{ testFeedback || '无法连接该地址' }}
      </p>
    </PopoverContent>
  </PopoverRoot>
</template>

<script setup lang="ts">
/**
 * Server status / config control.
 *
 * - Default: fixed top-right icon (EmptyLayout).
 * - `trust`: text action for the auth trust band.
 *
 * Never solid-primary; change-server is secondary.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { PopoverContent, PopoverRoot, PopoverTrigger } from '@/shared/ui/popover'
import { useServerConfig } from '@/shared/composables/useServerConfig'
import { Logger } from '@/shared/lib/logger'

const props = withDefaults(defineProps<{
  mode?: 'floating' | 'trust'
}>(), {
  mode: 'floating',
})

const { serverUrl: currentServerUrl, testServerConnection } = useServerConfig()
const router = useRouter()

const currentServerLabel = computed(() => currentServerUrl.value || '未配置服务器')

const actionLabel = computed(() => {
  if (props.mode === 'trust') {
    return currentServerUrl.value ? '配置' : '去配置'
  }
  return currentServerUrl.value ? '管理' : '配置'
})

const triggerAriaLabel = computed(() => {
  if (props.mode === 'trust') {
    return currentServerUrl.value ? '配置服务器地址' : '去配置服务器'
  }
  const state = currentServerUrl.value ? '已配置' : '未配置'
  return `服务器：${state}，点击查看或修改`
})

const testing = ref(false)
const popoverOpen = ref(false)
const testResult = ref<'ok' | 'fail' | null>(null)
const testFeedback = ref('')
const testedUrl = ref('')

const hasFreshSuccess = computed(() => (
  testResult.value === 'ok' && testedUrl.value === currentServerUrl.value
))

const connectionStateLabel = computed(() => {
  if (hasFreshSuccess.value) return '连接正常'
  return currentServerUrl.value ? '地址已保存' : '未配置'
})

watch(currentServerUrl, () => {
  testResult.value = null
  testFeedback.value = ''
  testedUrl.value = ''
})

const goToServerConfig = () => {
  popoverOpen.value = false
  void router.push('/server-config')
}

const handleTest = async () => {
  if (!currentServerUrl.value) return
  testing.value = true
  testResult.value = null
  testFeedback.value = ''
  try {
    const targetUrl = currentServerUrl.value
    const result = await testServerConnection(targetUrl)
    testResult.value = result.ok ? 'ok' : 'fail'
    testedUrl.value = targetUrl
    if (!result.ok) testFeedback.value = result.message
  } catch (err) {
    Logger.warn('[ServerStatusButton] Test failed', err)
    testResult.value = 'fail'
    testFeedback.value = '测试失败，请检查网络'
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
/* ─── Trigger ──────────────────────────────────────────────────────────── */
.server-status-trigger {
  position: fixed;
  top: calc(0.75rem + env(safe-area-inset-top, 0px));
  right: calc(0.75rem + env(safe-area-inset-right, 0px));
  z-index: var(--z-popover, 1100);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  background: hsl(var(--card) / 0.78);
  border: 1px solid hsl(var(--border) / 0.65);
  border-radius: 999px;
  color: hsl(var(--muted-foreground));
  box-shadow: 0 1px 2px hsl(var(--foreground) / 0.06);
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

@media (min-width: 640px) {
  .server-status-trigger {
    top: calc(1rem + env(safe-area-inset-top, 0px));
    right: calc(1rem + env(safe-area-inset-right, 0px));
  }
}

.server-status-trigger:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--card) / 0.9);
  border-color: hsl(var(--border));
  transform: translateY(-1px);
}

.server-status-trigger:active {
  transform: translateY(0);
}

.server-status-trigger--open {
  color: var(--app-selection-fg);
  border-color: var(--app-selection-border);
  background: hsl(var(--card) / 0.95);
}

.server-status-trigger__icon {
  width: 1rem;
  height: 1rem;
}

.server-status-trigger__label {
  color: inherit;
  font-size: var(--app-text-sm);
  font-weight: 600;
  white-space: nowrap;
}

.server-status-trigger--trust {
  position: relative;
  inset: auto;
  z-index: auto;
  width: auto;
  height: 2rem;
  padding-inline: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: var(--radius-md);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.88);
  box-shadow: none;
}

.server-status-trigger--trust:hover,
.server-status-trigger--trust.server-status-trigger--open {
  border-color: hsl(var(--border));
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground));
  transform: none;
}

.server-status-trigger--trust .server-status-trigger__icon {
  display: none;
}

/* ─── Popover ──────────────────────────────────────────────────────────── */
.server-status-popover {
  width: 17.5rem;
  padding: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: hsl(var(--popover));
  border: 1px solid hsl(var(--border) / 0.75);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.server-status-popover--trust {
  border-color: hsl(var(--border) / 0.82);
  box-shadow: var(--shadow-md);
}

.server-status-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.server-status-popover__eyebrow {
  font-family: var(--font-sans);
  font-size: var(--app-text-sm);
  font-weight: 600;
  color: hsl(var(--muted-foreground));
}

.server-status-popover__state {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: var(--app-text-sm);
  font-weight: 600;
}

.server-status-popover__state--ok {
  /* Healthy / configured — success semantic (DESIGN §2), not primary brand. */
  color: hsl(var(--success));
}
.server-status-popover__state--idle {
  color: hsl(var(--muted-foreground));
}

.server-status-popover__state-dot {
  width: 0.4375rem;
  height: 0.4375rem;
  border-radius: 50%;
  background: currentColor;
}

.server-status-popover__url {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.625rem 0.75rem;
  background: hsl(var(--muted) / 0.4);
  border: 1px solid hsl(var(--border) / 0.65);
  border-radius: var(--radius-md);
}

.server-status-popover__url-label {
  font-size: var(--app-text-xs);
  font-weight: 500;
  color: hsl(var(--muted-foreground));
}

.server-status-popover__url-value {
  font-family: var(--font-mono);
  font-size: var(--app-text-md);
  font-weight: 500;
  color: hsl(var(--foreground));
  word-break: break-all;
  line-height: 1.4;
}

.server-status-popover__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4375rem;
}

.server-status-popover__action {
  gap: 0.4375rem;
  width: 100%;
  justify-content: center;
}

.server-status-popover__action-icon {
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
}

.server-status-popover__feedback {
  display: inline-flex;
  align-items: center;
  gap: 0.4375rem;
  margin: 0;
  padding: 0.4375rem 0.625rem;
  border-radius: var(--radius-md);
  font-size: var(--app-text-sm);
  font-weight: 500;
  line-height: 1.4;
}

.server-status-popover__feedback--ok {
  color: hsl(var(--success));
  background: hsl(var(--success) / 0.1);
}

.server-status-popover__feedback--err {
  color: hsl(var(--destructive));
  background: hsl(var(--destructive) / 0.08);
}

.server-status-popover__feedback-icon {
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
}
</style>
