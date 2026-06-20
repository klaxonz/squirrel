<template>
  <Transition name="oauth-prompt">
    <div
      v-if="prompt.visible"
      class="fixed bottom-6 right-6 z-toast w-[min(24rem,calc(100vw-2rem))] rounded-md border border-border/60 bg-background p-4 text-foreground shadow-xl"
    >
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-sm font-semibold">
            <AppIcon name="link" class="h-4 w-4" />
            <span>YouTube TV 授权</span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">在授权页输入此代码</p>
        </div>
        <Button variant="ghost" size="icon" class="h-7 w-7 rounded-md text-muted-foreground" title="关闭" @click="$emit('dismiss')">
          <AppIcon name="close" class="h-4 w-4" />
        </Button>
      </div>

      <div class="mt-3 flex items-center gap-2">
        <div class="min-w-0 flex-1 select-all rounded-md border border-border/50 bg-muted px-3 py-2 font-mono text-lg font-semibold text-foreground">
          {{ prompt.userCode }}
        </div>
        <Button variant="outline" size="icon" class="h-10 w-10 rounded-md" title="复制授权码" @click="$emit('copy')">
          <AppIcon name="clipboard" class="h-4 w-4" />
        </Button>
      </div>

      <div class="mt-3 flex items-center justify-between gap-2">
        <span class="text-xs text-muted-foreground">{{ prompt.copied ? '已复制' : '等待授权完成' }}</span>
        <Button variant="outline" class="h-8 rounded-md text-xs" @click="$emit('open', prompt.verificationUrl)">
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
.oauth-prompt-enter-active,
.oauth-prompt-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.oauth-prompt-enter-from,
.oauth-prompt-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}
</style>
