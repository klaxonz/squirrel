<template>
  <div class="skeleton-container space-y-4">
    <div v-for="i in count" :key="i" class="skeleton-item">
      <div class="flex items-center gap-4">
        <!-- Avatar Placeholder -->
        <div class="w-10 h-10 bg-white/5 rounded-lg animate-pulse"></div>
        
        <div class="flex-1 space-y-2">
          <!-- Title Placeholder -->
          <div class="h-3 bg-white/10 w-1/3 rounded animate-pulse"></div>
          <!-- Meta Placeholder -->
          <div class="h-2 bg-white/5 w-1/2 rounded animate-pulse"></div>
        </div>
      </div>
      
      <!-- Metrics Placeholder -->
      <div class="flex gap-6 mt-4 ml-14">
        <div v-for="j in 3" :key="j" class="h-2 w-12 bg-white/5 rounded animate-pulse"></div>
      </div>
      
      <!-- Scanning Line Decoration -->
      <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-20"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  count?: number
}>(), {
  count: 3
})
</script>

<style scoped>
.skeleton-item {
  position: relative;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.03);
  overflow: hidden;
}

/* Subtle scanning sweep */
.skeleton-item::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.03),
    transparent
  );
  animation: sweep 3s infinite linear;
}

@keyframes sweep {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
  100% { transform: translateX(100%); }
}
</style>
