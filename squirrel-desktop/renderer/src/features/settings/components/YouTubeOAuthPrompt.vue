<template>
  <Transition name="oauth-prompt">
    <div
      v-if="prompt.visible"
      class="oauth-prompt"
    >
      <div class="oauth-prompt__header">
        <div class="oauth-prompt__copy">
          <div class="oauth-prompt__title">
            <AppIcon name="link" class="h-4 w-4" />
            <span>YouTube TV 授权</span>
          </div>
          <p class="oauth-prompt__description">在授权页输入此代码</p>
        </div>
        <Button text variant="secondary" size="sm" icon-only class="text-muted-foreground" title="关闭" @click="$emit('dismiss')">
          <AppIcon name="close" class="h-4 w-4" />
        </Button>
      </div>

      <div class="oauth-prompt__code-row">
        <div class="app-surface app-surface--subtle oauth-prompt__code">
          {{ prompt.userCode }}
        </div>
        <Button variant="secondary" outlined size="sm" icon-only title="复制授权码" @click="$emit('copy')">
          <AppIcon name="clipboard" class="h-4 w-4" />
        </Button>
      </div>

      <div class="oauth-prompt__footer">
        <span class="oauth-prompt__status">{{ prompt.copied ? '已复制' : '等待授权完成' }}</span>
        <Button variant="secondary" outlined size="sm" @click="$emit('open', prompt.verificationUrl)">
          <AppIcon name="externalLink" class="h-3.5 w-3.5" />
          打开授权页
        </Button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
/**
 * Floating YouTube TV-code OAuth prompt. Slides up from the bottom-right while
 * a device-authorization flow is in progress. Extracted from
 * SiteRuntimeManager.vue (was an inline 35-line block). Pure presentational —
 * all actions are emitted; the owning view wires them to useYouTubeOAuth.
 *
 * Note: uses z-toast (was z-50) so the prompt layers correctly above content
 * but below any active toast/dialog.
 */
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

defineProps<{
  prompt: {
    visible: boolean
    userCode: string
    copied: boolean
    verificationUrl: string
  }
}>()

defineEmits<{
  dismiss: []
  copy: []
  open: [url: string]
}>()
</script>

<style scoped>
/* OAuth prompt banner — slides up from the bottom-right. Deliberately NOT named
   `toast-*` so it can't collide with the global toast stack's `app-toast-*`. */
.oauth-prompt {
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  z-index: var(--z-toast);
  width: min(24rem, calc(100vw - 2rem));
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-toast-radius);
  background: hsl(var(--popover));
  color: hsl(var(--foreground));
  padding: var(--app-toast-padding);
  box-shadow: var(--app-floating-shadow);
}

.oauth-prompt__header,
.oauth-prompt__code-row,
.oauth-prompt__footer {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.oauth-prompt__header {
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.oauth-prompt__copy {
  min-width: 0;
}

.oauth-prompt__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: hsl(var(--foreground));
  font-size: var(--app-text-base);
  font-weight: 650;
}

.oauth-prompt__description,
.oauth-prompt__status {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.oauth-prompt__description {
  margin: var(--space-1) 0 0;
}

.oauth-prompt__code-row,
.oauth-prompt__footer {
  margin-top: var(--space-3);
}

.oauth-prompt__code {
  min-width: 0;
  flex: 1;
  user-select: all;
  padding: var(--space-2) var(--space-3);
  color: hsl(var(--foreground));
  font-family: var(--font-mono);
  font-size: var(--app-text-xl);
  font-weight: 700;
}

.oauth-prompt__footer {
  justify-content: space-between;
}

.oauth-prompt-enter-active,
.oauth-prompt-leave-active {
  transition: opacity var(--duration-base) var(--ease-default), transform var(--duration-base) var(--ease-default);
}

.oauth-prompt-enter-from,
.oauth-prompt-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}

@media (prefers-reduced-motion: reduce) {
  .oauth-prompt-enter-active,
  .oauth-prompt-leave-active {
    transition: none;
  }
}
</style>
