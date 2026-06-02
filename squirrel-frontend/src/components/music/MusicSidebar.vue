<template>
  <aside class="music-sidebar">
    <div class="music-sidebar-header">
      <AppIcon name="playlistMusic" class="h-6 w-6 text-primary" />
      <span class="music-sidebar-title">音乐</span>
    </div>

    <nav class="music-sidebar-nav">
      <section class="music-nav-group">
        <h3 class="music-nav-group-title">发现</h3>
        <ul class="music-nav-list">
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'home' }"
              @click="$emit('navigate', 'home')"
            >
              <AppIcon name="home" class="h-5 w-5" />
              <span>首页</span>
            </button>
          </li>
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'fm' }"
              @click="$emit('navigate', 'fm')"
            >
              <AppIcon name="star" class="h-5 w-5" />
              <span>私人 FM</span>
            </button>
          </li>
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'everyday' }"
              @click="$emit('navigate', 'everyday')"
            >
              <AppIcon name="bolt" class="h-5 w-5" />
              <span>每日推荐</span>
            </button>
          </li>
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'ai' }"
              @click="$emit('navigate', 'ai')"
            >
              <AppIcon name="star" class="h-5 w-5" />
              <span>AI 推荐</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="music-nav-group">
        <h3 class="music-nav-group-title">音乐库</h3>
        <ul class="music-nav-list">
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'ranks' }"
              @click="$emit('navigate', 'ranks')"
            >
              <AppIcon name="list" class="h-5 w-5" />
              <span>排行榜</span>
            </button>
          </li>
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'playlists' }"
              @click="$emit('navigate', 'playlists')"
            >
              <AppIcon name="playlistMusic" class="h-5 w-5" />
              <span>歌单广场</span>
            </button>
          </li>
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'new_albums' }"
              @click="$emit('navigate', 'new_albums')"
            >
              <AppIcon name="playlistMusic" class="h-5 w-5" />
              <span>新碟上架</span>
            </button>
          </li>
          <li>
            <button
              class="music-nav-link"
              :class="{ 'music-nav-link--active': activeMode === 'new_songs' }"
              @click="$emit('navigate', 'new_songs')"
            >
              <AppIcon name="bolt" class="h-5 w-5" />
              <span>新歌速递</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="music-nav-group" v-if="userPlaylists.length">
        <h3 class="music-nav-group-title">我的歌单</h3>
        <ul class="music-nav-list">
          <li>
            <button
              class="music-nav-link music-nav-link--playlist"
              :class="{ 'music-nav-link--active': selectedUserPlaylist?.id === playlist.id }"
              v-for="playlist in userPlaylists.slice(0, 10)"
              :key="playlist.id"
              @click="$emit('select-playlist', playlist)"
            >
              <AppIcon name="playlistMusic" class="h-4 w-4" />
              <span class="truncate">{{ playlist.name }}</span>
              <span class="music-nav-count">{{ playlist.song_count }}</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="music-nav-group">
        <h3 class="music-nav-group-title">创建歌单</h3>
        <div class="music-create-playlist">
          <input
            v-model="newPlaylistName"
            type="text"
            class="music-create-input"
            placeholder="新歌单名称"
            maxlength="20"
          />
          <button
            class="music-create-btn"
            :disabled="!newPlaylistName.trim()"
            @click="handleCreate"
          >
            <AppIcon name="plus" class="h-4 w-4" />
          </button>
        </div>
      </section>
    </nav>

    <div class="music-sidebar-footer">
      <button
        class="music-nav-link"
        :class="{ 'music-nav-link--active': activeMode === 'profile' }"
        @click="$emit('navigate', 'profile')"
      >
        <AppIcon name="user" class="h-5 w-5" />
        <span>{{ authStatus?.logged_in ? '个人中心' : '登录' }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicUserPlaylist, MusicAuthStatus } from '@/api/music'

defineProps<{
  activeMode: string
  userPlaylists: MusicUserPlaylist[]
  selectedUserPlaylist: MusicUserPlaylist | null
  authStatus: MusicAuthStatus | null
}>()

const emit = defineEmits<{
  'navigate': [mode: string]
  'select-playlist': [playlist: MusicUserPlaylist]
  'create-playlist': [name: string]
}>()

const newPlaylistName = ref('')

function handleCreate() {
  const name = newPlaylistName.value.trim()
  if (!name) return
  emit('create-playlist', name)
  newPlaylistName.value = ''
}
</script>

<style scoped>
.music-sidebar {
  width: 240px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: hsl(var(--card));
  border-right: 1px solid hsl(var(--border));
}

.music-sidebar-header {
  padding: 1.25rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-bottom: 1px solid hsl(var(--border));
}

.music-sidebar-title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.music-nav-group {
  padding: 0.75rem 0;
}

.music-nav-group-title {
  padding: 0.25rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  letter-spacing: 0.05em;
}

.music-nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.music-nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  width: 100%;
  border: none;
  background: none;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.music-nav-link:hover {
  background: hsl(var(--accent) / 0.5);
}

.music-nav-link--active {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.music-nav-link--playlist {
  gap: 0.5rem;
  padding: 0.375rem 1rem;
  font-size: 0.8125rem;
}

.music-nav-count {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  margin-left: auto;
}

.music-create-playlist {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 1rem;
}

.music-create-input {
  flex: 1;
  padding: 0.375rem 0.5rem;
  font-size: 0.8125rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  outline: none;
}

.music-create-input:focus {
  border-color: hsl(var(--primary));
}

.music-create-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 0.375rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  cursor: pointer;
}

.music-create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.music-sidebar-footer {
  padding: 0.75rem 0;
  border-top: 1px solid hsl(var(--border));
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