<template>
  <div class="empty-container">
    <div class="empty-shell">
      <div class="empty-content">
        <span class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-20"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
        </span>
        <p class="empty-title">{{ title }}</p>
        <p class="empty-message">{{ message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  message: string
}>(), {
  title: ''
})
</script>

<style scoped>
.empty-container {
  padding: 1rem 0.5rem;
  width: 100%;
}

.empty-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  text-align: center;
}

.empty-icon {
  color: hsl(var(--muted-foreground) / 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-title {
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground) / 0.25);
}

.empty-message {
  font-size: 9px;
  font-weight: 500;
  color: hsl(var(--muted-foreground) / 0.2);
  max-width: 180px;
}
</style>
