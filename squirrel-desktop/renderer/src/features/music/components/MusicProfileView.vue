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
        <Button size="sm" @click="$emit('retry')">
          重试
        </Button>
      </template>
    </AppEmptyState>

    <div v-else-if="!authStatus?.logged_in" class="music-login-showcase">
      <slot name="login" />
    </div>

    <div v-else-if="profile" class="music-profile-layout">
      <header class="music-profile-banner">
        <div class="music-profile-identity">
          <div class="music-profile-avatar-wrap">
            <img
              v-if="profile?.avatar"
              :src="profile.avatar"
              :alt="profileName ? `${profileName}的头像` : '用户头像'"
              class="music-profile-avatar"
            />
            <div v-else class="music-profile-avatar-fallback">
              <AppIcon name="user" class="h-6 w-6" />
            </div>
            <span v-if="profile?.level" class="music-profile-level-badge">LV.{{ profile.level }}</span>
          </div>

          <div class="music-profile-banner-info">
            <div class="music-profile-name-row">
              <h2 class="music-profile-nickname">{{ profileName }}</h2>
              <span v-if="profile?.gender" class="music-gender-tag">
                {{ profile.gender === '1' ? '男' : (profile.gender === '2' ? '女' : '保密') }}
              </span>
            </div>
            <div class="music-profile-meta">
              <span v-if="profileIdentity" class="music-profile-id">ID {{ profileIdentity }}</span>
              <span v-if="profile?.register_time" class="music-reg-date">{{ formatRegTime(profile.register_time) }} 注册</span>
              <span v-if="error" class="music-profile-warning">{{ error }}</span>
            </div>
          </div>
        </div>

        <div class="music-profile-banner-stats" aria-label="账号统计">
          <div class="music-profile-stat-item">
            <span class="music-profile-stat-num">{{ profile?.follow_count ?? 0 }}</span>
            <span class="music-profile-stat-name">关注</span>
          </div>
          <div class="music-profile-stat-item">
            <span class="music-profile-stat-num">{{ profile?.fan_count ?? 0 }}</span>
            <span class="music-profile-stat-name">粉丝</span>
          </div>
          <div class="music-profile-stat-item">
            <span class="music-profile-stat-num">{{ profile?.listen_count ?? 0 }}</span>
            <span class="music-profile-stat-name">累计听歌</span>
          </div>
        </div>

        <Button
          text severity="secondary"
          size="sm"
          class="music-profile-logout"
          :loading="logoutLoading"
          @click="$emit('logout')"
        >
          <AppIcon v-if="!logoutLoading" name="logout" class="h-3.5 w-3.5" />
          退出
        </Button>
      </header>

      <TabsRoot
        v-model:value="activeTab"
        class="music-profile-tabs-wrapper"
      >
        <div class="music-profile-tabs-header">
          <TabsList class="music-profile-tabs-list">
            <TabsTrigger value="playlists" class="music-profile-tab-btn">
              <span>我的歌单</span>
            </TabsTrigger>
            <TabsTrigger value="history" class="music-profile-tab-btn">
              <span>最近播放</span>
            </TabsTrigger>
            <TabsTrigger value="rank" class="music-profile-tab-btn">
              <span>听歌排行</span>
            </TabsTrigger>
          </TabsList>

          <div class="music-profile-tab-actions">
            <MusicCreatePlaylistDialog
              v-if="activeTab === 'playlists'"
              :on-create="createPlaylist"
            />

            <Button
              v-if="activeTab !== 'playlists' && currentProfileTracks.length > 0"
              variant="secondary"
              size="sm"
              @click="$emit('play-all-profile', activeTab, false)"
            >
              <AppIcon name="play" class="h-3.5 w-3.5" />
              播放全部
            </Button>
          </div>
        </div>

      <div class="music-profile-panel">
        <TabsContent value="playlists" class="music-profile-playlists">
          <div class="music-profile-playlist-section">
            <div class="music-profile-section-header">
              <h3 class="music-profile-section-title">创建的歌单 ({{ createdPlaylists.length }})</h3>
            </div>
            <AppEmptyState
              v-if="createdPlaylists.length === 0"
              class="music-profile-playlist-empty"
              variant="plain"
              icon="playlistMusic"
              title="还没有创建歌单"
              copy="创建一个歌单，用来整理和持续收听喜欢的歌曲。"
            />
            <div v-else class="app-music-grid">
              <MusicCard
                v-for="playlist in createdPlaylists"
                :key="playlist.listid"
                :cover="playlist.pic ? formatMusicImageUrl(playlist.pic) : undefined"
                :title="playlist.name"
                :subtitle="`${playlist.m_count || playlist.count || 0} 首歌曲`"
                variant="playlist"
                @select="$emit('select-playlist', playlist)"
              />
            </div>
          </div>

          <div class="music-profile-playlist-section mt-8">
            <h3 class="music-profile-section-title">收藏的歌单 ({{ collectedPlaylists.length }})</h3>
            <div v-if="collectedPlaylists.length === 0" class="music-profile-playlist-empty">
              暂无收藏歌单，浏览热门歌单并收藏后将在此显示
            </div>
            <div v-else class="app-music-grid">
              <MusicCard
                v-for="playlist in collectedPlaylists"
                :key="playlist.listid"
                :cover="playlist.pic ? formatMusicImageUrl(playlist.pic) : undefined"
                :title="playlist.name"
                :subtitle="`${playlist.m_count || playlist.count || 0} 首歌曲`"
                variant="playlist"
                @select="$emit('select-playlist', playlist)"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="history" class="music-profile-tracks-list">
          <AppBlockLoader v-if="historyLoading" size="sm" text="正在载入播放历史..." />
          <AppEmptyState v-else-if="history.length === 0" class="py-12" variant="plain" icon="playlistMusic" title="暂无播放历史记录" />
          <MusicTrackList
            v-else
            :tracks="pagedHistory"
            :show-mv="false"
            :show-related="false"
            :show-selection="false"
            :index-offset="(historyPage - 1) * PROFILE_TRACKS_PAGE_SIZE"
            :target-playlist-id="targetPlaylistId"
            @select-artist="$emit('select-artist', $event)"
            @add-to-playlist="$emit('add-to-playlist', $event)"
          />
          <div v-if="historyTotalPages > 1" class="music-profile-pagination" aria-label="最近播放分页">
            <span class="music-profile-pagination__meta">
              第 {{ historyPage }} / {{ historyTotalPages }} 页 · 共 {{ history.length }} 首
            </span>
            <div class="music-profile-pagination__actions">
              <Button severity="secondary" size="sm" :disabled="historyPage === 1" @click="historyPage -= 1">
                上一页
              </Button>
              <Button severity="secondary" size="sm" :disabled="historyPage === historyTotalPages" @click="historyPage += 1">
                下一页
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="rank" class="music-profile-tracks-list">
          <AppBlockLoader v-if="rankLoading" size="sm" text="正在载入听歌排行..." />
          <AppEmptyState v-else-if="listenRank.length === 0" class="py-12" variant="plain" icon="playlistMusic" title="暂无听歌排行数据" />
          <MusicTrackList
            v-else
            :tracks="pagedListenRank"
            :show-mv="false"
            :show-related="false"
            :show-selection="false"
            :index-offset="(rankPage - 1) * PROFILE_TRACKS_PAGE_SIZE"
            :target-playlist-id="targetPlaylistId"
            @select-artist="$emit('select-artist', $event)"
            @add-to-playlist="$emit('add-to-playlist', $event)"
          />
          <div v-if="rankTotalPages > 1" class="music-profile-pagination" aria-label="听歌排行分页">
            <span class="music-profile-pagination__meta">
              第 {{ rankPage }} / {{ rankTotalPages }} 页 · 共 {{ listenRank.length }} 首
            </span>
            <div class="music-profile-pagination__actions">
              <Button severity="secondary" size="sm" :disabled="rankPage === 1" @click="rankPage -= 1">
                上一页
              </Button>
              <Button severity="secondary" size="sm" :disabled="rankPage === rankTotalPages" @click="rankPage += 1">
                下一页
              </Button>
            </div>
          </div>
        </TabsContent>
      </div>
      </TabsRoot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import MusicTrackList from './MusicTrackList.vue'
import MusicCard from './shared/MusicCard.vue'
import MusicCreatePlaylistDialog from './profile/MusicCreatePlaylistDialog.vue'
import { formatMusicImageUrl, formatRegTime } from '@/features/music/lib/musicFormatters'
import type { MusicUserProfile, MusicUserPlaylist, MusicTrack, MusicAuthStatus } from '@/shared/api/music'

const props = defineProps<{
  profile: MusicUserProfile | null
  authStatus: MusicAuthStatus | null
  userPlaylists: MusicUserPlaylist[]
  history: MusicTrack[]
  listenRank: MusicTrack[]
  historyLoading: boolean
  rankLoading: boolean
  loading: boolean
  error: string
  logoutLoading: boolean
  targetPlaylistId: string
  createPlaylist: (name: string) => Promise<boolean>
}>()

defineEmits<{
  'retry': []
  'logout': []
  'play-all-profile': [category: 'history' | 'rank', shuffle: boolean]
  'select-playlist': [playlist: MusicUserPlaylist]
  'select-artist': [track: MusicTrack]
  'add-to-playlist': [track: MusicTrack]
}>()

const PROFILE_TRACKS_PAGE_SIZE = 20

const activeTab = ref<'playlists' | 'history' | 'rank'>('playlists')
const historyPage = ref(1)
const rankPage = ref(1)

const profileName = computed(() => props.profile?.nickname || '已登录账号')
const profileIdentity = computed(() => props.profile?.userid || props.authStatus?.userid || '')
const createdPlaylists = computed(() => props.userPlaylists.filter(pl => Number(pl.type || 0) !== 1))
const collectedPlaylists = computed(() => props.userPlaylists.filter(pl => Number(pl.type || 0) === 1))
const currentProfileTracks = computed(() => activeTab.value === 'history' ? props.history : props.listenRank)

const pageCount = (total: number) => Math.max(1, Math.ceil(total / PROFILE_TRACKS_PAGE_SIZE))
const pageItems = (tracks: MusicTrack[], page: number) => {
  const start = (page - 1) * PROFILE_TRACKS_PAGE_SIZE
  return tracks.slice(start, start + PROFILE_TRACKS_PAGE_SIZE)
}

const historyTotalPages = computed(() => pageCount(props.history.length))
const rankTotalPages = computed(() => pageCount(props.listenRank.length))
const pagedHistory = computed(() => pageItems(props.history, historyPage.value))
const pagedListenRank = computed(() => pageItems(props.listenRank, rankPage.value))

watch(() => props.history.length, () => {
  historyPage.value = Math.min(historyPage.value, historyTotalPages.value)
})

watch(() => props.listenRank.length, () => {
  rankPage.value = Math.min(rankPage.value, rankTotalPages.value)
})

watch(activeTab, (tab) => {
  if (tab === 'history') historyPage.value = Math.min(historyPage.value, historyTotalPages.value)
  if (tab === 'rank') rankPage.value = Math.min(rankPage.value, rankTotalPages.value)
})

// ponytail: formatRegTime (Kugou registration-time normaliser, handles both
// epoch-seconds and datetime-string shapes) is imported from the shared
// musicFormatters lib.
</script>

<style scoped>
.music-profile-view {
  width: 100%;
}

.music-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
}

.music-login-showcase {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
}

.music-profile-layout {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.music-profile-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 2rem;
  min-height: 6.25rem;
  padding: 1.125rem 1.5rem;
  border-block: 1px solid hsl(var(--border) / 0.24);
  background: linear-gradient(180deg, hsl(var(--muted) / 0.18), transparent);
}

.music-profile-identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 1rem;
}

.music-profile-avatar-wrap {
  position: relative;
  flex: 0 0 auto;
}

.music-profile-avatar {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  object-fit: cover;
  border: 1px solid hsl(var(--border) / 0.36);
}

.music-profile-avatar-fallback {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted) / 0.22);
  border: 1px solid hsl(var(--border) / 0.32);
}

.music-profile-level-badge {
  position: absolute;
  right: -0.375rem;
  bottom: -0.25rem;
  font-size: var(--app-text-badge-size);
  font-weight: 600;
  padding: 0.125rem 0.4375rem;
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.375rem;
}

.music-profile-banner-info {
  flex: 1 1 auto;
  min-width: 0;
  text-align: left;
}

.music-profile-name-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
}

.music-profile-nickname {
  margin: 0;
  overflow: hidden;
  color: var(--app-heading-color);
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  letter-spacing: var(--app-h3-tracking);
  line-height: var(--app-h3-leading);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-profile-meta {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 0.625rem;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-profile-id {
  color: hsl(var(--muted-foreground));
}

.music-gender-tag {
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.4375rem;
  border: 1px solid hsl(var(--border) / 0.28);
  border-radius: var(--radius-sm);
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 500;
}

.music-reg-date {
  font-size: 0.6875rem;
}

.music-profile-warning {
  color: hsl(var(--destructive));
  font-size: 0.6875rem;
}

.music-profile-logout {
  justify-self: end;
  color: hsl(var(--muted-foreground));
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-weight: 500;
}

.music-profile-logout:hover {
  border-color: hsl(var(--border) / 0.34);
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--foreground));
}

.music-profile-banner-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(4.75rem, 1fr));
  gap: 0;
  min-width: 20rem;
  border-left: 1px solid hsl(var(--border) / 0.28);
}

.music-profile-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.1875rem;
  min-height: 3rem;
  padding: 0 1rem;
  border-right: 1px solid hsl(var(--border) / 0.2);
  background: transparent;
}

.music-profile-stat-item:last-child {
  border-right: 0;
}

.music-profile-stat-num {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  line-height: 1.2;
}

.music-profile-stat-name {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
}

.music-profile-tabs-wrapper {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.75rem;
}

.music-profile-tabs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 3rem;
  padding: 0.5rem 1.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.2);
}

.music-profile-tabs {
  display: flex;
  gap: 0.25rem;
}

/* Match shared Tabs / AppSegmentedControl: secondary track + card active. */
.music-profile-tabs-list {
  display: inline-flex;
  gap: 2px;
  border: none;
  background: hsl(var(--secondary));
  box-shadow: none;
  padding: 2px;
  border-radius: var(--radius-md);
}

.music-profile-tab-btn {
  padding: 0.25rem 0.75rem;
  min-height: 1.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.music-profile-tab-btn:hover {
  color: hsl(var(--foreground));
}

.music-profile-tab-btn[data-state="active"] {
  color: hsl(var(--foreground));
  background: hsl(var(--card));
  box-shadow: var(--shadow-xs);
}

@media (prefers-reduced-motion: reduce) {
  .music-profile-tab-btn {
    transition: none;
  }
}

.music-profile-tab-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2rem;
}

.music-profile-panel {
  width: 100%;
  min-height: 200px;
}

.music-profile-playlists {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 0 1.5rem;
}

.music-profile-playlist-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.music-profile-section-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 1rem;
  min-height: 2rem;
}

.music-profile-section-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.music-profile-playlist-empty {
  min-height: 13rem;
  border: 1px dashed hsl(var(--border) / 0.5);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--muted) / 0.12);
}

.music-profile-tracks-list {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.music-profile-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.875rem 1.5rem 0;
}

.music-profile-pagination__meta {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.music-profile-pagination__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 860px) {
  .music-profile-banner {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
  }

  .music-profile-banner-stats {
    grid-column: 1 / -1;
    width: 100%;
    min-width: 0;
    border-left: 0;
    border-top: 1px solid hsl(var(--border) / 0.2);
    padding-top: 0.75rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .music-profile-tab-btn {
    transition: none;
  }
}
</style>
