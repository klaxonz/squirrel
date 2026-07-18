<template>
  <div>
    <!-- Floating trigger: collapsed icon button anchored to the viewport
         top-right. Hidden until useServerConfig has resolved. -->
    <button
      type="button"

      :class="['server-status-trigger', { 'server-status-trigger--open': popoverOpen }]"
      :title="currentServerLabel"
      :aria-label="triggerAriaLabel"
      @click="togglePopover"
    >
      <span
        class="server-status-trigger__dot"
        :class="{ 'server-status-trigger__dot--idle': !currentServerUrl }"
        aria-hidden="true"
      />
      <AppIcon name="server" class="server-status-trigger__icon" />
    </button>

    <PrimePopover
      ref="serverPopover"
      class="server-status-popover"
      @show="popoverOpen = true"
      @hide="popoverOpen = false"
    >
      <header class="server-status-popover__head">
        <span class="server-status-popover__eyebrow">后端引擎</span>
        <span
          class="server-status-popover__state"
          :class="currentServerUrl
            ? 'server-status-popover__state--ok'
            : 'server-status-popover__state--idle'"
        >
          <span class="server-status-popover__state-dot" />
          {{ currentServerUrl ? '已连接' : '未配置' }}
        </span>
      </header>

      <div class="server-status-popover__url">
        <span class="server-status-popover__url-label">当前地址</span>
        <code class="server-status-popover__url-value">{{ currentServerLabel }}</code>
      </div>

      <div class="server-status-popover__actions">
        <Button
          type="button"
          severity="secondary" outlined
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
          as="router-link"
          to="/server-config"
          size="sm"
          class="server-status-popover__action server-status-popover__action--primary"
        >
          <AppIcon name="settingsPanel" class="server-status-popover__action-icon" />
          <span>{{ currentServerUrl ? '更换服务器' : '去配置服务器' }}</span>
        </Button>
      </div>

      <p
        v-if="testResult === 'ok'"
        class="server-status-popover__feedback server-status-popover__feedback--ok"
      >
        <AppIcon name="statusSuccess" class="server-status-popover__feedback-icon" />
        后端服务响应正常
      </p>
      <p
        v-else-if="testResult === 'fail'"
        class="server-status-popover__feedback server-status-popover__feedback--err"
      >
        <AppIcon name="warning" class="server-status-popover__feedback-icon" />
        {{ testFeedback || '无法连接至该地址' }}
      </p>
    </PrimePopover>
  </div>
</template>

<script setup lang="ts">
/**
 * Floating "server status" affordance for the auth surface.
 *
 * Replaces the inline `auth-brand__server-pill` that used to sit in the brand
 * panel's top bar. That pill had three problems:
 *   1. Visually lived on the left panel but the user reads it as "right side"
 *      because brand panels are usually navigation, not chrome.
 *   2. Always showed the full URL even when the user just wanted a glance at
 *      "is the server reachable".
 *   3. Mixed two concerns (display + edit) into one clickable element.
 *
 * This component collapses to a compact icon button anchored to the viewport
 * top-right corner, with a status dot carrying the real semantic state. Click
 * opens a popover that shows the URL, a quick "Test connection" probe, and
 * the "Change server" action.
 */
import { computed, ref } from 'vue'
import PrimePopover from 'primevue/popover'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useServerConfig } from '@/shared/composables/useServerConfig'
import { Logger } from '@/shared/lib/logger'

const { serverUrl: currentServerUrl, testServerConnection } = useServerConfig()

const currentServerLabel = computed(() => currentServerUrl.value || '未配置服务器')
const triggerAriaLabel = computed(() => {
  const state = currentServerUrl.value ? '已连接' : '未配置'
  return `后端服务器：${state}，点击查看或修改`
})

const testing = ref(false)
const serverPopover = ref<{ toggle: (event: Event) => void } | null>(null)
const popoverOpen = ref(false)
const testResult = ref<'ok' | 'fail' | null>(null)
const testFeedback = ref('')

const togglePopover = (event: Event) => {
  serverPopover.value?.toggle(event)
}

const handleTest = async () => {
  if (!currentServerUrl.value) return
  testing.value = true
  testResult.value = null
  testFeedback.value = ''
  try {
    const result = await testServerConnection(currentServerUrl.value)
    testResult.value = result.ok ? 'ok' : 'fail'
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
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.4);
  background: hsl(var(--card) / 0.95);
}

.server-status-trigger__icon {
  width: 1rem;
  height: 1rem;
}

.server-status-trigger__dot {
  position: absolute;
  top: 0.3125rem;
  right: 0.3125rem;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  /* Configured endpoint present — operational readiness, not brand accent. */
  background: hsl(var(--success));
  box-shadow: 0 0 0 2px hsl(var(--card) / 0.9);
}

.server-status-trigger__dot--idle {
  background: hsl(var(--muted-foreground));
  box-shadow: 0 0 0 2px hsl(var(--card) / 0.9);
}

/* ─── Popover ──────────────────────────────────────────────────────────── */
.server-status-popover {
  width: 18rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  /* Surface pulls up to --card so the popover reads as a raised panel against
     the auth shell's warm wash. We deliberately omit a border: in dark mode
     any hairline (--border, currentColor, white — pick your poison) reads as
     a stark outline and breaks the floating-card illusion. A layered shadow
     does the lifting work instead, which is the convention Linear / Vercel /
     GitHub use for their popovers: a tight ambient shadow + a long, soft drop
     so the panel feels physically above the page, not stamped onto it. */
  background: hsl(var(--card));
  border: 0;
  border-radius: var(--radius-lg);
  box-shadow:
    0 1px 2px hsl(var(--foreground) / 0.08),
    0 12px 28px hsl(var(--foreground) / 0.22),
    0 32px 64px -12px hsl(var(--foreground) / 0.32);
}

.server-status-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.server-status-popover__eyebrow {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
}

.server-status-popover__state {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
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
  font-size: 0.6875rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
}

.server-status-popover__url-value {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
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
}

.server-status-popover__action--primary {
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
  font-size: 0.75rem;
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
