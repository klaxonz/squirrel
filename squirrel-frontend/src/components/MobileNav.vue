<template>
  <nav class="fixed bottom-0 left-0 right-0 bg-bg-primary border-t border-border-primary h-nav">
    <ul class="flex justify-around h-full items-center">
      <li v-for="route in routes" :key="route.path">
        <router-link
          :to="route.path"
          class="flex flex-col items-center px-4"
          :class="{ 'text-text-accent': $route.path === route.path, 'text-text-muted': $route.path !== route.path }"
        >
          <component :is="route.icon" class="w-6 h-6" />
          <span class="text-2xs mt-1">{{ route.name }}</span>
        </router-link>
      </li>
    </ul>
  </nav>
</template>

<script setup>
defineProps({
  routes: {
    type: Array,
    required: true
  }
});
</script>

<style scoped>
.router-link-active {
  color: var(--text-accent);
}
</style>
