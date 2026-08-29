<template>
  <AppPageShell class="not-found" variant="compact" surface="operate" width="reading" fill>
    <main class="not-found__main" aria-labelledby="not-found-title">
      <AppEmptyState
        variant="plain"
        icon="panelOpen"
        icon-circle
        title="这里没有可显示的内容"
        copy="地址可能已失效，或页面已经移动。你可以返回上一页，或回到首页继续浏览。"
      >
        <template #actions>
          <Button v-if="navigation.canGoBack.value" variant="outline" @click="goBack">
            <AppIcon name="chevronLeft" class="size-4" />
            返回上一页
          </Button>
          <Button @click="goHome">
            <AppIcon name="home" class="size-4" />
            回到首页
          </Button>
        </template>
      </AppEmptyState>
    </main>
  </AppPageShell>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
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
  display: flex;
  min-height: 100%;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--app-page-gutter);
}

.not-found :deep(.app-empty-state) {
  width: 100%;
  min-height: 22rem;
}
</style>
