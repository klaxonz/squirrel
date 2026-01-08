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
        同步
      </button>

      <div
        v-show="panelOpen"
        id="refresh-center-panel"
        class="panel"
        role="region"
        aria-label="同步中心"
      >
        <div class="panel-header">
          <span>同步中心</span>
          <button class="close" @click="panelOpen = false">✕</button>
        </div>
        <ul class="list scrollbar">
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
import { useSubscriptionRefresh } from '../composables/useSubscriptionRefresh';
import { useImageFallback } from '../composables/useImageFallback';

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
  background: #202020;
  color: #fff;
  border: 1px solid #2f2f2f;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
}
.dot::after {
  content: attr(data-count);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #cc0000;
  color: #fff;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  font-size: 12px;
}
.panel {
  margin-top: 8px;
  width: 320px;
  background: #181818;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 8px 0;
  box-shadow: 0 16px 40px rgba(0,0,0,.5);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  color: #e5e5e5;
}
.close { color: #aaa; }
.list { max-height: 360px; overflow: auto; }
.item { display: flex; gap: 10px; padding: 10px 12px; }
.item + .item { border-top: 1px solid #242424; }
.item img { width: 28px; height: 28px; border-radius: 999px; }
.meta { flex: 1; min-width: 0; }
.title { font-size: 13px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub { font-size: 12px; color: #9a9a9a; margin-top: 2px; }
.bar { height: 6px; background: #2a2a2a; border-radius: 999px; margin-top: 6px; overflow: hidden; }
.progress { height: 100%; background: #cc0000; width: 0; transition: width .4s ease; }
</style>


