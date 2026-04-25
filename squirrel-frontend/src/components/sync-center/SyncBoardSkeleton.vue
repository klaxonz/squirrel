<template>
  <div class="skeleton-container">
    <div v-for="i in count" :key="i" class="skeleton-item">
      <div class="skeleton-item__identity">
        <div class="skeleton-item__avatar animate-pulse"></div>

        <div class="min-w-0 flex-1 space-y-2">
          <div class="h-3 w-1/3 rounded animate-pulse skeleton-surface"></div>
          <div class="h-2 w-1/2 rounded animate-pulse skeleton-surface"></div>
        </div>
      </div>

      <div class="skeleton-item__metrics">
        <div v-for="j in 3" :key="j" class="h-2 w-8 rounded animate-pulse skeleton-surface"></div>
      </div>

      <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-foreground/10 to-transparent opacity-20"></div>
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
.skeleton-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skeleton-surface {
  background: hsl(var(--foreground) / 0.05);
}

.skeleton-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  min-height: 3.5rem;
  padding: 0.6rem 1rem;
  background: transparent;
  border: none;
  overflow: hidden;
}

.skeleton-item__identity {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
  flex: 1;
}

.skeleton-item__avatar {
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  background: hsl(var(--foreground) / 0.05);
}

.skeleton-item__metrics {
  display: flex;
  flex-shrink: 0;
  align-items: flex-end;
  gap: 1.5rem;
  opacity: 0.5;
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
    hsl(var(--foreground) / 0.03),
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
