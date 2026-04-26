<template>
  <section class="route-context-bar" aria-label="页面上下文">
    <nav v-if="breadcrumbs.length" class="route-context-bar__breadcrumbs" aria-label="面包屑">
      <template v-for="(item, index) in breadcrumbs" :key="`${item.label}-${index}`">
        <router-link
          v-if="item.to"
          :to="item.to"
          class="route-context-bar__crumb route-context-bar__crumb--link"
        >
          {{ item.label }}
        </router-link>
        <span v-else class="route-context-bar__crumb route-context-bar__crumb--current">
          {{ item.label }}
        </span>
        <span
          v-if="index < breadcrumbs.length - 1"
          class="route-context-bar__separator"
          aria-hidden="true"
        >
          /
        </span>
      </template>
    </nav>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { BreadcrumbItem } from '@/constants/sidebar'

defineProps({
  sectionLabel: {
    type: String,
    default: '',
  },
  pageTitle: {
    type: String,
    required: true,
  },
  breadcrumbs: {
    type: Array as PropType<BreadcrumbItem[]>,
    default: () => [],
  },
})
</script>

<style scoped>
.route-context-bar {
  display: flex;
  align-items: center;
  padding: 0.85rem 2rem 0;
}

.route-context-bar__breadcrumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  min-width: 0;
}

.route-context-bar__crumb {
  font-size: 0.6875rem;
  line-height: 1.4;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.route-context-bar__crumb--link {
  color: hsl(var(--muted-foreground));
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-default);
}

.route-context-bar__crumb--link:hover {
  color: hsl(var(--foreground));
}

.route-context-bar__crumb--current {
  color: hsl(var(--foreground));
  font-weight: 600;
}

.route-context-bar__separator {
  color: hsl(var(--muted-foreground) / 0.55);
  font-size: 0.625rem;
}

@media (max-width: 767px) {
  .route-context-bar {
    padding: 0.75rem 1rem 0;
  }
}
</style>
