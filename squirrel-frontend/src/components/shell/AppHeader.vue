<template>
  <header class="h-14 sticky top-0 z-40 flex items-center px-6 gap-4 bg-background">
    <div class="flex items-center gap-4 flex-1 min-w-0">
      <div v-if="!showSearch" class="flex items-center overflow-hidden">
        <RouteContextBar 
          :page-title="routeContext.pageTitle" 
          :breadcrumbs="routeContext.breadcrumbs"
          :section-label="routeContext.sectionLabel"
        />
      </div>
      
      <div v-else class="flex-1 max-w-2xl mx-auto flex justify-center">
        <GlobalSearchBar />
      </div>
    </div>
    
    <div class="flex items-center gap-1">
      <button class="w-8 h-8 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-all active:scale-95 relative group">
        <AppIcon name="notification" class="w-4 h-4" />
        <span class="absolute top-2 right-2 w-1.5 h-1.5 bg-destructive rounded-full border border-background shadow-sm" />
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import RouteContextBar from '@/components/layout/RouteContextBar.vue'
import GlobalSearchBar from '@/components/layout/GlobalSearchBar.vue'
import { resolveRouteContext } from '@/constants/sidebar'

const route = useRoute()
const showSearch = computed(() => !!route.meta?.showSearch)
const routeContext = computed(() => resolveRouteContext(route))
</script>
