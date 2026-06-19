<template>
  <component :is="layout">
    <router-view v-slot="{ Component, route }">
      <Transition name="page">
        <keep-alive :include="keepAliveIncludes">
          <component :is="Component" :key="(route.meta.transitionKey as string) ?? route.path" />
        </keep-alive>
      </Transition>
    </router-view>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import EmptyLayout from './layouts/EmptyLayout.vue'

const route = useRoute()
const router = useRouter()

const keepAliveIncludes = Array.from(new Set(
  router
    .getRoutes()
    .map((routeRecord) => routeRecord.meta.keepAliveComponent)
    .filter((componentName): componentName is string => typeof componentName === 'string'),
))

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
  overflow: hidden;
  background: hsl(var(--background));
}

#app {
  height: 100%;
}
</style>
