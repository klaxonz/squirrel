<template>
  <component :is="layout">
    <router-view v-slot="{ Component }">
      <keep-alive :include="['LatestVideos', 'Subscribed']">
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import EmptyLayout from './layouts/EmptyLayout.vue'

const route = useRoute()

const layouts = {
  default: AppLayout,
  auth: AuthLayout,
  empty: EmptyLayout
}

const layout = computed(() => {
  const layoutName = (route.meta.layout as string) || 'default'
  return layouts[layoutName as keyof typeof layouts] || layouts.default
})
</script>

<style>
/* Lock the viewport for App-like feel */
html, body {
  margin: 0;
  padding: 0;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: hsl(var(--background));
}

#app {
  height: 100%;
}
</style>
