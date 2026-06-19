<template>
  <div class="music-profile-view">
    <AppBlockLoader v-if="loading && !profile" text="加载主页中..." />
    
    <AppEmptyState
      v-else-if="error && !profile"
      variant="plain"
      icon="warning"
      title="加载失败"
      :copy="error"
    >
      <template #actions>
        <Button class="h-8 rounded-md px-3 text-xs" @click="$emit('retry')">
          重试
        </Button>
      </template>
    </AppEmptyState>
    
    <div v-else-if="!authStatus?.logged_in" class="music-login-showcase">
      <slot name="login" />
    </div>
    
    <div v-else-if="profile" class="music-profile-layout">
      <header class="music-profile-banner">
        <div class="music-profile-banner-glass">
          <div class="music-profile-avatar-wrap">
            <img v-if="profile.avatar" :src="profile.avatar" :alt="profile.nickname ? `${profile.nickname}的头像` : '用户头像'" class="music-profile-avatar" />
            <div v-else class="music-profile-avatar-fallback">
              <AppIcon name="user" class="h-10 w-10 text-primary" />
            </div>
            <span class="music-profile-level-badge">LV.{{ profile.level }}</span>
          </div>
          
          <div class="music-profile-banner-info">
            <h2 class="music-profile-nickname">{{ profile.nickname || '酷狗用户' }}</h2>
            <p class="music-profile-gender-reg">
              <span v-if="profile.gender" class="music-gender-tag">{{ profile.gender === '1' ? '♂ 男' : (profile.gender === '2' ? '♀ 女' : '密') }}</span>
              <span v-if="profile.register_time" class="music-reg-date">注册时间: {{ formatRegTime(profile.register_time) }}</span>
              <Button
                variant="ghost"
                size="sm"
                class="h-6 px-2 rounded-md text-xs text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors ml-1 font-semibold flex items-center gap-1 shrink-0"
                :loading="logoutLoading"
                @click="$emit('logout')"
              >
                <AppIcon v-if="!logoutLoading" name="logout" class="h-3 w-3" />
                退出登录
              </Button>
            </p>
          </div>
          
          <div class="music-profile-banner-stats">
            <div class="music-profile-stat-item">
              <span class="music-profile-stat-num">{{ profile.follow_count }}</span>
              <span class="music-profile-stat-name">关注</span>
            </div>
            <div class="music-profile-stat-item">
              <span class="music-profile-stat-num">{{ profile.fan_count }}</span>
              <span class="music-profile-stat-name">粉丝</span>
            </div>
            <div class="music-profile-stat-item">
              <span class="music-profile-stat-num">{{ profile.listen_count }}</span>
              <span class="music-profile-stat-name">累计听歌</span>
            </div>
          </div>
        </div>
      </header>
      
      <Tabs
        :value="activeTab"
        class="music-profile-tabs-wrapper"
        @update:value="activeTab = $event as 'playlists' | 'history' | 'rank'"
      >
        <TabsList class="music-profile-tabs-list">
          <TabsTrigger value="playlists" class="music-profile-tab-btn" :class="{ 'active': activeTab === 'playlists' }">
            <span>我的歌单</span>
          </TabsTrigger>
          <TabsTrigger value="history" class="music-profile-tab-btn" :class="{ 'active': activeTab === 'history' }">
            <span>最近播放</span>
          </TabsTrigger>
          <TabsTrigger value="rank" class="music-profile-tab-btn" :class="{ 'active': activeTab === 'rank' }">
            <span>听歌排行</span>
          </TabsTrigger>
        </TabsList>

        <div class="music-profile-tab-actions">
          <button
            v-if="activeTab !== 'playlists' && currentProfileTracks.length > 0"
            class="music-chip music-chip--primary"
            @click="$emit('play-all-profile', false)"
          >
            <AppIcon name="play" class="h-3.5 w-3.5" />
            播放全部
          </button>

          <div v-if="activeTab === 'rank'" class="music-profile-rank-pills">
            <button
              class="music-profile-rank-pill"
              :class="{ 'active': rankType === 0 }"
              @click="$emit('toggle-rank-type', 0)"
            >最近一周</button>
            <button
              class="music-profile-rank-pill"
              :class="{ 'active': rankType === 1 }"
              @click="$emit('toggle-rank-type', 1)"
            >全部累计</button>
          </div>
        </div>
      
      <div class="music-profile-panel">
        <TabsContent value="playlists" class="music-profile-playlists">
          <div class="music-profile-playlist-section">
            <h3 class="music-profile-section-title">创建的歌单 ({{ createdPlaylists.length }})</h3>
            <div v-if="createdPlaylists.length === 0" class="music-profile-playlist-empty">
              暂无自建歌单，您可以在顶部创建歌单
            </div>
            <div v-else class="music-grid">
              <div
                v-for="playlist in createdPlaylists"
                :key="playlist.id"
                class="music-grid-card"
                role="button"
                tabindex="0"
                @click="$emit('select-playlist', playlist)"
                @keydown.enter.prevent="$emit('select-playlist', playlist)"
                @keydown.space.prevent="$emit('select-playlist', playlist)"
              >
                <div class="music-source-cover-wrap">
                  <img v-if="playlist.cover" :src="playlist.cover" :alt="playlist.name" class="music-source-cover" />
                  <div v-else class="music-source-cover">
                    <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div class="music-source-play-overlay">
                    <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
                  </div>
                </div>
                <span class="music-grid-card-title">{{ playlist.name }}</span>
                <span class="music-grid-card-subtitle">{{ playlist.song_count }} 首歌曲</span>
              </div>
            </div>
          </div>

          <div class="music-profile-playlist-section mt-8">
            <h3 class="music-profile-section-title">收藏的歌单 ({{ collectedPlaylists.length }})</h3>
            <div v-if="collectedPlaylists.length === 0" class="music-profile-playlist-empty">
              暂无收藏歌单，浏览热门歌单并收藏后将在此显示
            </div>
            <div v-else class="music-grid">
              <div
                v-for="playlist in collectedPlaylists"
                :key="playlist.id"
                class="music-grid-card"
                role="button"
                tabindex="0"
                @click="$emit('select-playlist', playlist)"
                @keydown.enter.prevent="$emit('select-playlist', playlist)"
                @keydown.space.prevent="$emit('select-playlist', playlist)"
              >
                <div class="music-source-cover-wrap">
                  <img v-if="playlist.cover" :src="playlist.cover" :alt="playlist.name" class="music-source-cover" />
                  <div v-else class="music-source-cover">
                    <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div class="music-source-play-overlay">
                    <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
                  </div>
                </div>
                <span class="music-grid-card-title">{{ playlist.name }}</span>
                <span class="music-grid-card-subtitle">{{ playlist.song_count }} 首歌曲</span>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="history" class="music-profile-tracks-list">
          <AppBlockLoader v-if="historyLoading" size="sm" text="正在载入播放历史..." />
          <AppEmptyState v-else-if="history.length === 0" class="py-12" variant="plain" icon="playlistMusic" title="暂无播放历史记录" />
          <MusicTrackList
            v-else
            :tracks="history"
            :show-mv="false"
            :show-related="false"
            :target-playlist-id="targetPlaylistId"
            @select-artist="$emit('select-artist', $event)"
            @add-to-playlist="$emit('add-to-playlist', $event)"
          />
        </TabsContent>

        <TabsContent value="rank" class="music-profile-tracks-list">
          <AppBlockLoader v-if="rankLoading" size="sm" text="正在载入听歌排行..." />
          <AppEmptyState v-else-if="listenRank.length === 0" class="py-12" variant="plain" icon="playlistMusic" title="暂无听歌排行数据" />
          <MusicTrackList
            v-else
            :tracks="listenRank"
            :show-mv="false"
            :show-related="false"
            :target-playlist-id="targetPlaylistId"
            @select-artist="$emit('select-artist', $event)"
            @add-to-playlist="$emit('add-to-playlist', $event)"
          />
        </TabsContent>
      </div>
      </Tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/ui/tabs'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import MusicTrackList from './MusicTrackList.vue'
import type { MusicUserProfile, MusicUserPlaylist, MusicTrack, MusicAuthStatus } from '@/shared/api/music'

const props = defineProps<{
  profile: MusicUserProfile | null
  authStatus: MusicAuthStatus | null
  userPlaylists: MusicUserPlaylist[]
  history: MusicTrack[]
  listenRank: MusicTrack[]
  historyLoading: boolean
  rankLoading: boolean
  rankType: 0 | 1
  loading: boolean
  error: string
  logoutLoading: boolean
  targetPlaylistId: string
}>()

defineEmits<{
  'retry': []
  'logout': []
  'toggle-rank-type': [type: 0 | 1]
  'play-all-profile': [shuffle: boolean]
  'select-playlist': [playlist: MusicUserPlaylist]
  'select-artist': [track: MusicTrack]
  'add-to-playlist': [track: MusicTrack]
}>()

const activeTab = ref<'playlists' | 'history' | 'rank'>('playlists')

const createdPlaylists = computed(() => props.userPlaylists.filter(pl => !pl.is_collected))
const collectedPlaylists = computed(() => props.userPlaylists.filter(pl => pl.is_collected))
const currentProfileTracks = computed(() => activeTab.value === 'history' ? props.history : props.listenRank)

function formatRegTime(val: string): string {
  if (!val) return ''
  if (/^\d+$/.test(val)) {
    const d = new Date(Number(val) * 1000)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }
  return val.split(' ')[0] || val
}
</script>

<style scoped>
.music-profile-view {
  padding: 1rem;
}

.music-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.music-login-showcase {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.music-profile-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.music-profile-banner {
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: hsl(var(--card) / 0.5);
  border: 1px solid hsl(var(--border) / 0.3);
}

.music-profile-banner-glass {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.music-profile-avatar-wrap {
  position: relative;
}

.music-profile-avatar {
  width: 4rem;
  height: 4rem;
  border-radius: 9999px;
  object-fit: cover;
  border: 2px solid hsl(var(--primary) / 0.3);
}

.music-profile-avatar-fallback {
  width: 4rem;
  height: 4rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--muted) / 0.4);
}

.music-profile-level-badge {
  position: absolute;
  bottom: -0.25rem;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.625rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-radius: 9999px;
}

.music-profile-banner-info {
  text-align: center;
}

.music-profile-nickname {
  font-size: 1.125rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-profile-gender-reg {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 0.375rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-gender-tag {
  padding: 0.125rem 0.375rem;
  background: hsl(var(--muted) / 0.4);
  border-radius: 0.25rem;
}

.music-reg-date {
  font-size: 0.6875rem;
}

.music-profile-banner-stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
}

.music-profile-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.music-profile-stat-num {
  font-size: 1.25rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-profile-stat-name {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
}

.music-profile-tabs-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.2);
}

.music-profile-tabs {
  display: flex;
  gap: 0.25rem;
}

.music-profile-tabs-list {
  display: inline-flex;
  gap: 0.25rem;
  border: none;
  background: transparent;
  box-shadow: none;
  padding: 0;
}

.music-profile-tab-btn {
  padding: 0.5rem 1rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.3);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-profile-tab-btn:hover {
  color: hsl(var(--foreground));
}

.music-profile-tab-btn.active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.music-profile-tab-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.music-chip {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  background: hsl(var(--muted) / 0.5);
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-chip:hover {
  background: hsl(var(--muted) / 0.7);
}

.music-chip--primary {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.music-profile-rank-pills {
  display: flex;
  gap: 0.25rem;
}

.music-profile-rank-pill {
  padding: 0.375rem 0.625rem;
  font-size: 0.6875rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.3);
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-profile-rank-pill:hover {
  color: hsl(var(--foreground));
}

.music-profile-rank-pill.active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.music-profile-panel {
  min-height: 200px;
}

.music-profile-playlists {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.music-profile-playlist-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.music-profile-section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.music-profile-playlist-empty {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  padding: 1rem;
  background: hsl(var(--muted) / 0.2);
  border-radius: 0.375rem;
}

.music-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 1rem;
}

.music-grid-card {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.music-grid-card:hover {
  transform: translateY(-2px);
}

.music-source-cover-wrap {
  position: relative;
  aspect-ratio: 1;
  border-radius: 0.5rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-source-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-source-play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--foreground) / 0.3);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.music-grid-card:hover .music-source-play-overlay {
  opacity: 1;
}

.music-grid-card-title {
  font-size: 0.8125rem;
  font-weight: 500;
  margin-top: 0.5rem;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-grid-card-subtitle {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-profile-tracks-list {
  display: flex;
  flex-direction: column;
}
</style>
