<template>
  <nav class="fixed bottom-0 left-0 right-0 bg-[#0f0f0f] border-t border-[#272727] h-[64px]">
    <ul class="flex justify-around h-full items-center">
      <li v-for="route in routes" :key="route.path">
        <router-link 
          :to="route.path" 
          class="flex flex-col items-center px-4"
          :class="{ 'text-white': $route.path === route.path, 'text-[#909090]': $route.path !== route.path }"
        >
          <component :is="route.icon" class="w-6 h-6" />
          <span class="text-[10px] mt-1">{{ route.name }}</span>
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
  color: #fff;
}
</style> 