<template>
  <AppPageShell class="not-found" variant="compact" surface="operate" width="fluid" fill>
    <main class="not-found__main" aria-labelledby="not-found-title">
      <div class="not-found__status" aria-hidden="true">
        <span>404</span>
      </div>

      <div class="not-found__content">
        <p class="not-found__eyebrow">页面未找到</p>
        <h1 id="not-found-title">这里没有可显示的内容</h1>
        <p class="not-found__copy">
          地址可能已失效，或页面已经移动。你可以返回上一页，或回到首页继续浏览。
        </p>
        <div class="not-found__actions">
          <Button v-if="navigation.canGoBack.value" severity="secondary" outlined @click="goBack">
            <AppIcon name="chevronLeft" class="size-4" />
            返回上一页
          </Button>
          <Button @click="goHome">
            <AppIcon name="home" class="size-4" />
            回到首页
          </Button>
        </div>
      </div>
    </main>
  </AppPageShell>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'

const router = useRouter()
const navigation = useNavigationHistory()

async function goBack() {
  const navigated = await navigation.goBack()
  if (!navigated) await router.replace({ name: 'HomeView' })
}

function goHome() {
  void router.push({ name: 'HomeView' })
}
</script>

<style scoped>
.not-found__main {
  display: grid;
  width: min(100%, 64rem);
  min-height: 100%;
  margin-inline: auto;
  grid-template-columns: minmax(12rem, 0.7fr) minmax(18rem, 1fr);
  align-items: center;
  gap: clamp(2rem, 7vw, 6rem);
  padding: clamp(2rem, 8vh, 6rem) var(--app-page-gutter);
}

.not-found__status {
  display: flex;
  min-height: 15rem;
  align-items: center;
  justify-content: center;
  border-right: 1px solid hsl(var(--border));
  color: hsl(var(--muted-foreground) / 0.32);
  font-family: var(--font-mono);
  font-size: clamp(4.5rem, 8rem, 8rem);
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0;
  user-select: none;
}

.not-found__content {
  max-width: 31rem;
}

.not-found__eyebrow {
  margin: 0 0 var(--space-3);
  color: hsl(var(--primary));
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0;
}

.not-found h1 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: clamp(1.75rem, 2.25rem, 2.25rem);
  font-weight: 750;
  line-height: 1.2;
  letter-spacing: 0;
}

.not-found__copy {
  margin: var(--space-4) 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.9375rem;
  line-height: 1.75;
}

.not-found__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

@media (max-width: 639px) {
  .not-found__main {
    grid-template-columns: 1fr;
    align-content: center;
    gap: var(--space-5);
    padding-inline: var(--space-5);
  }

  .not-found__status {
    min-height: auto;
    justify-content: flex-start;
    border-right: 0;
    border-bottom: 1px solid hsl(var(--border));
    padding-bottom: var(--space-5);
    font-size: 4.5rem;
  }

  .not-found__actions {
    align-items: stretch;
    flex-direction: column-reverse;
  }

  .not-found__actions :deep(.sq-button) {
    width: 100%;
  }
}
</style>
