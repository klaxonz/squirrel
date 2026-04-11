<template>
  <router-link
    :to="item.path"
    class="menu-item-neon"
    :class="{ 'is-active': isActive }"
  >
    <div class="menu-item-content">
      <div class="icon-wrapper">
        <component
          :is="item.icon"
          class="menu-icon"
          aria-hidden="true"
        />
      </div>
      <div class="label-wrapper">
        <span class="menu-index">{{ formattedIndex }}</span>
        <span class="menu-label">{{ item.name }}</span>
      </div>
    </div>
    <div class="menu-active-glow"></div>
  </router-link>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})

const formattedIndex = computed(() => {
  return props.index < 10 ? `0${props.index}` : props.index
})
</script>

<style scoped>
.menu-item-neon {
  --neon-primary: hsl(var(--primary));
  --neon-primary-glow: hsl(var(--primary) / 0.8);
  --neon-primary-bg: hsl(var(--primary) / 0.05);

  position: relative;
  display: flex;
  padding: 1.25rem 1rem;
  color: hsl(var(--sidebar-foreground) / 0.5);
  text-decoration: none;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  border-bottom: 1px solid hsl(var(--sidebar-border) / 0.3);
  overflow: hidden;
}

.menu-item-neon:hover {
  color: hsl(var(--sidebar-foreground));
  background: hsl(var(--sidebar-accent));
}

.menu-item-neon:hover .menu-icon {
  transform: translateX(2px);
  color: var(--neon-primary);
}

.is-active {
  color: hsl(var(--sidebar-accent-foreground));
  background: hsl(var(--primary) / 0.08);
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 2;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
}

.menu-icon {
  width: 1.25rem;
  height: 1.25rem;
  transition: all 0.3s ease;
}

.is-active .menu-icon {
  color: hsl(var(--primary));
  filter: drop-shadow(0 0 8px hsl(var(--primary) / 0.4));
  animation: pulse 2s infinite ease-in-out;
}

.label-wrapper {
  display: flex;
  flex-direction: column;
}

.menu-index {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  letter-spacing: 0.1em;
  opacity: 0.4;
  margin-bottom: -0.1rem;
}

.is-active .menu-label {
  font-weight: 700;
}

.menu-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.menu-active-glow {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--neon-primary);
  opacity: 0;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  box-shadow: 0 0 15px var(--neon-primary);
}

.is-active .menu-active-glow {
  opacity: 1;
  height: 100%;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.05); }
}
</style>
