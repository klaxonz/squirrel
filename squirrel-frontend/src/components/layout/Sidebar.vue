<template>
  <aside class="w-[var(--sidebar-width)] h-full flex flex-col bg-zinc-50/50 dark:bg-zinc-950/30 border-r border-border select-none">
    <!-- Brand Section (Premium Minimalist) -->
    <div class="h-16 flex items-center px-4 mt-2 mb-4">
      <router-link to="/" class="flex items-center gap-3 px-2 group w-full">
        <div class="w-8 h-8 bg-primary text-primary-foreground rounded-lg flex items-center justify-center shadow-[0_2px_10px_rgb(0,0,0,0.1)] transition-transform duration-300 group-hover:scale-105 group-active:scale-95">
          <AppIcon name="brand" class="w-4 h-4" />
        </div>
        <span class="text-[15px] font-bold tracking-tight text-foreground">松鼠</span>
      </router-link>
    </div>

    <!-- Navigation Groups -->
    <nav class="flex-1 overflow-y-auto px-3 space-y-6 scrollbar-hide pb-8">
      <div v-for="group in NAV_GROUPS" :key="group.key">
        <div class="px-2 mb-2 flex items-center justify-between">
          <span class="text-[11px] font-semibold tracking-wider text-muted-foreground/60 uppercase">
            {{ group.label }}
          </span>
        </div>
        <div class="space-y-1">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
          />
        </div>
      </div>
    </nav>

    <!-- User Section (Premium Style) -->
    <div class="p-4 border-t border-border mt-auto bg-zinc-100/50 dark:bg-zinc-900/30">
      <div class="flex items-center gap-3 p-2 -m-2 rounded-xl hover:bg-white dark:hover:bg-zinc-800 transition-all duration-200 cursor-pointer group hover:shadow-sm border border-transparent hover:border-border" @click="handleLogout">
        <div class="relative w-9 h-9 shrink-0">
          <div class="w-full h-full rounded-full bg-white dark:bg-zinc-700 flex items-center justify-center border border-border shadow-sm text-xs font-bold text-foreground overflow-hidden uppercase group-hover:border-primary/30 transition-colors">
            <template v-if="userInitial">
              {{ userInitial }}
            </template>
            <AppIcon v-else name="user" class="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
        
        <div class="flex-1 min-w-0">
          <p class="text-[13px] font-semibold truncate text-foreground leading-tight">{{ userDisplayName }}</p>
          <p class="text-[11px] text-muted-foreground truncate leading-tight mt-0.5">{{ userEmail }}</p>
        </div>
        
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity bg-muted/50 group-hover:bg-muted">
          <AppIcon name="logout" class="w-3.5 h-3.5" />
        </div>
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
  if (!userStore.currentUser) return '请先登录'
  return userStore.currentUser.email || '高级会员'
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