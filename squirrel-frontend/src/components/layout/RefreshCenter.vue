<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-50" v-if="activeItems.length">
      <button
        class="refresh-fab"
        @click="panelOpen = !panelOpen"
        :aria-expanded="panelOpen"
        aria-controls="refresh-center-panel"
      >
        <span class="dot" :data-count="activeItems.length"></span>
        同步提醒
      </button>

      <div
        v-show="panelOpen"
        id="refresh-center-panel"
        class="panel"
        role="region"
        aria-label="同步提醒"
      >
        <div class="panel-header">
          <span>同步提醒</span>
          <button class="close" @click="panelOpen = false">✕</button>
        </div>
        <ul class="list scrollbar-hide">
          <li v-for="item in activeItems" :key="item.id" class="item">
            <img :src="getAvatarSrc(item.meta?.avatar, item.id)" alt="" referrerpolicy="no-referrer" @error="(e) => handleAvatarError(e, item.id)" />
            <div class="meta">
              <div class="title">{{ item.meta?.name || ('订阅 ' + item.id) }}</div>
              <div class="sub">
                {{ getStatusText(item.state.status, item.state.phase) }}
                <span v-if="item.state.total"> · {{ item.state.processed }}/{{ item.state.total }}</span>
              </div>
              <div class="bar">
                <div class="progress" :style="{ width: progress(item.state) + '%' }"></div>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </Teleport>
  </template>

<script setup>
import { computed, ref } from 'vue';
import { useImageFallback } from '@/composables/useImageFallback'
import { useSubscriptionRefresh } from '@/composables/useSubscriptionRefresh'

const panelOpen = ref(false);
const { refreshStates, subscriptionMeta, getStatusText, getProgressPercentage } = useSubscriptionRefresh();
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();

const activeItems = computed(() => {
  const items = [];
  refreshStates.forEach((state, id) => {
    if (state.isRefreshing || state.status === 'queued' || state.status === 'in_progress') {
      items.push({ id, state, meta: subscriptionMeta.get(id) });
    }
  });
  return items;
});

const progress = (state) => getProgressPercentage(state.processed, state.total);
</script>

<style scoped>
.refresh-fab {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  padding: 8px 14px;
  font-size: var(--font-size-xs);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--shadow-lg);
}
.dot::after {
  content: attr(data-count);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--primary));
  color: hsl(var(--foreground));
  width: 18px;
  height: 18px;
  border-radius: 999px;
  font-size: var(--font-size-2xs);
}
.panel {
  margin-top: 8px;
  width: 320px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 12px;
  padding: 8px 0;
  box-shadow: var(--shadow-popup);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  color: hsl(var(--foreground));
}
.close { color: hsl(var(--muted-foreground)); }
.list { max-height: 360px; overflow: auto; }
.item { display: flex; gap: 10px; padding: 10px 12px; }
.item + .item { border-top: 1px solid hsl(var(--border)); }
.item img { width: 28px; height: 28px; border-radius: calc(var(--radius-sm) - 1px); }
.meta { flex: 1; min-width: 0; }
.title { font-size: var(--font-size-xs); color: hsl(var(--foreground)); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub { font-size: var(--font-size-2xs); color: hsl(var(--muted-foreground)); margin-top: 2px; }
.bar { height: 6px; background: hsl(var(--muted)); border-radius: 999px; margin-top: 6px; overflow: hidden; }
.progress { height: 100%; background: hsl(var(--primary)); width: 0; transition: width .4s ease; }
</style>


