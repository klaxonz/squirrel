<template>
  <aside class="w-[var(--sidebar-width)] h-full flex flex-col bg-sidebar border-r border-border/40 select-none">
    <!-- Brand Section (Minimalist Style) -->
    <div class="h-14 flex items-center px-4 mb-2">
      <router-link to="/" class="flex items-center gap-2 group">
        <div class="w-6 h-6 bg-foreground rounded-md flex items-center justify-center transition-transform group-hover:scale-105 group-active:scale-95 shadow-sm">
          <AppIcon name="brand" class="w-3.5 h-3.5 text-background fill-current" />
        </div>
        <span class="text-[14px] font-bold tracking-tight text-foreground">松鼠</span>
      </router-link>
    </div>

    <!-- Navigation Groups -->
    <nav class="flex-1 overflow-y-auto px-2 space-y-6 scrollbar-hide pb-8">
      <div v-for="group in NAV_GROUPS" :key="group.key">
        <div class="px-3 mb-1.5 flex items-center justify-between">
          <span class="text-[10px] font-bold tracking-widest text-muted-foreground/40 uppercase">
            {{ group.label }}
          </span>
        </div>
        <div class="space-y-0.5">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
          />
        </div>
      </div>
    </nav>

    <!-- User Section (Integrated Style) -->
    <div class="p-3 border-t border-border/40 mt-auto">
      <div class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-secondary/50 transition-colors cursor-pointer group" @click="handleLogout">
        <div class="relative w-8 h-8 shrink-0">
          <div class="w-full h-full rounded-full bg-secondary flex items-center justify-center border border-border/50 text-xs font-bold text-foreground overflow-hidden uppercase">
            <template v-if="userInitial">
              {{ userInitial }}
            </template>
            <AppIcon v-else name="user" class="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
        
        <div class="flex-1 min-w-0">
          <p class="text-[12px] font-semibold truncate text-foreground/80">{{ userDisplayName }}</p>
          <p class="text-[10px] text-muted-foreground/60 truncate">{{ userEmail }}</p>
        </div>
        
        <AppIcon name="logout" class="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import { useUserStore } from '@/stores/user'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_GROUPS, isNavigationItemActive } from '@/constants/sidebar'

const router = useRouter()
const userStore = useUserStore()

const userDisplayName = computed(() => {
  if (!userStore.currentUser) return '未登录'
  return userStore.currentUser.nickname || userStore.currentUser.email?.split('@')[0] || '用户'
})

const userEmail = computed(() => {
  return userStore.currentUser?.email || '请先登录'
})

const userInitial = computed(() => {
  const name = userDisplayName.value
  return name && name !== '未登录' ? name.charAt(0) : ''
})

const handleLogout = async () => {
  await userStore.logout()
  router.push('/login')
}
</script>
