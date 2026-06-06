<template>
  <aside class="music-sidebar">
    <div class="music-sidebar-header">
      <div class="music-sidebar-logo">
        <AppIcon name="playlistMusic" class="h-5 w-5" />
      </div>
      <span class="music-sidebar-title">音乐</span>
    </div>

    <nav class="music-sidebar-nav">
      <MusicNavGroup
        title="主导航"
        :items="discoverItems"
        :active-id="activeMode"
        :default-expanded="true"
        @select="handleNavigate"
      />

      <MusicNavGroup
        title="浏览"
        :items="libraryItems"
        :active-id="activeMode"
        :default-expanded="true"
        @select="handleNavigate"
      />

      <MusicNavGroup
        v-if="authStatus?.logged_in"
        title="我的"
        :items="myItems"
        :active-id="activeMode"
        :default-expanded="true"
        @select="handleNavigate"
      >
        <MusicUserPlaylists
          :playlists="userPlaylists"
          :selected-id="selectedUserPlaylist?.id"
          @select="$emit('select-playlist', $event)"
        />
        <MusicCreatePlaylistButton @create="$emit('create-playlist', $event)" />
      </MusicNavGroup>

      <MusicNavGroup
        v-else
        title="我的"
        :items="loginItems"
        :active-id="activeMode"
        :default-expanded="true"
        @select="handleNavigate"
      />
    </nav>

    <div class="music-sidebar-footer"></div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { AppIconName } from '@/icons/app-icons'
import MusicNavGroup from './MusicNavGroup.vue'
import MusicUserPlaylists from './MusicUserPlaylists.vue'
import MusicCreatePlaylistButton from './MusicCreatePlaylistButton.vue'
import type { MusicUserPlaylist, MusicAuthStatus } from '@/api/music'

interface MusicSidebarItem {
  id: string
  label: string
  icon: AppIconName
}

defineProps<{
  activeMode: string
  userPlaylists: MusicUserPlaylist[]
  selectedUserPlaylist: MusicUserPlaylist | null
  authStatus: MusicAuthStatus | null
}>()

const emit = defineEmits<{
  navigate: [mode: string]
  'select-playlist': [playlist: MusicUserPlaylist]
  'create-playlist': [name: string]
}>()

const discoverItems: MusicSidebarItem[] = [
  { id: 'home', label: '首页', icon: 'home' },
]

const libraryItems: MusicSidebarItem[] = [
  { id: 'ranks', label: '排行榜', icon: 'list' },
  { id: 'playlists', label: '歌单广场', icon: 'playlistMusic' },
]

const myItems = computed<MusicSidebarItem[]>(() => [
  { id: 'favorites', label: '我喜欢的音乐', icon: 'heart' },
  { id: 'profile', label: '个人中心', icon: 'user' },
])

const loginItems: MusicSidebarItem[] = [
  { id: 'profile', label: '登录酷狗音乐', icon: 'user' },
]

function handleNavigate(id: string) {
  emit('navigate', id)
}
</script>

<style scoped>
.music-sidebar {
  width: 220px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: hsl(var(--background));
  border-right: 1px solid hsl(var(--border) / 0.4);
  position: relative;
  z-index: 2;
}

.music-sidebar-header {
  padding: 1.25rem 1rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  border-bottom: 1px solid hsl(var(--border) / 0.35);
  position: relative;
  z-index: 1;
}

.music-sidebar-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.875rem;
  height: 1.875rem;
  border-radius: 0.5rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  box-shadow: 0 2px 10px hsl(var(--foreground) / 0.1);
}

.music-sidebar-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  letter-spacing: -0.01em;
}

.music-sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 0;
}

.music-sidebar-nav::-webkit-scrollbar {
  width: 4px;
}

.music-sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}

.music-sidebar-nav::-webkit-scrollbar-thumb {
  background: hsl(var(--border));
  border-radius: 2px;
}

.music-sidebar-footer {
  padding: 0;
  border-top: 1px solid hsl(var(--border) / 0.35);
  margin-top: auto;
}

.music-nav-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  margin: 1px 0.75rem;
  width: calc(100% - 1.5rem);
  border: none;
  background: none;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  border-radius: 0.5rem;
  position: relative;
}

.music-nav-item:hover {
  background: hsl(var(--foreground) / 0.04);
  color: hsl(var(--foreground));
}

.music-nav-item--active {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground));
  font-weight: 600;
}

.music-nav-item--active :first-child {
  color: hsl(var(--primary));
}

@media (max-width: 1024px) {
  .music-sidebar {
    width: 200px;
  }
}

@media (max-width: 768px) {
  .music-sidebar {
    display: none;
  }
}
</style>
