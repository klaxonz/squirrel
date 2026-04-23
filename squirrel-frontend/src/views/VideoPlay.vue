
<template>
  <div ref="videoPageRef" class="video-page terminal-viewport scrollbar-hide" :class="{ 'is-widescreen': isWidescreen }">
    <div :class="['video-page__container', { 'is-widescreen': isWidescreen }]">
      <!-- 左侧主内容区域 -->
      <div class="video-main">
        <!-- 视频播放区域 -->
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
            <Transition name="fade-player" appear>
              <div class="viewfinder-box">
                <div class="viewfinder-corner viewfinder-corner--top-left"></div>
                <div class="viewfinder-corner viewfinder-corner--top-right"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-left"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-right"></div>
                <div
                  v-if="video || playbackSource || isResolvingPlayback || externalError"
                  ref="videoPlayerHostRef"
                  class="video-player-host"
                />
              </div>
            </Transition>
          </div>
        </div>

        <!-- 视频信息区域 -->
        <div ref="videoMetaRef" class="video-meta">
          <Transition name="fade-meta" mode="out-in">
            <div v-if="video" :key="video.id">
              <!-- 标题行 -->
              <div class="video-meta__headline">
                <h1 class="video-meta__title">
                  {{ video?.title }}
                </h1>
                <div v-if="videoPublishedText" class="video-meta__publish-date" title="发布时间">
                  <Icon icon="lucide:calendar-days" class="video-meta__publish-date-icon" />
                  <span>发布于 {{ videoPublishedText }}</span>
                </div>
              </div>

              <!-- 频道信息 + 操作按钮 -->
              <div class="video-meta__info-row">
                <!-- 频道信息 -->
                <div v-if="isVideoChannelVisible && video?.subscriptions?.[0]" class="video-channel">
                  <div class="video-channel__primary">
                    <div class="video-channel__avatar-wrapper">
                      <SubscriptionAvatar
                        :src="video.subscriptions[0].avatar"
                        :name="video.subscriptions[0].name"
                        size="lg"
                        class="video-channel__avatar"
                      />
                    </div>
                    <div class="video-channel__identity">
                      <router-link
                        v-if="video?.subscriptions?.[0]"
                        :to="`/subscription/${video.subscriptions[0].id}/all`"
                        class="video-channel__name"
                      >
                        {{ video.subscriptions[0].name }}
                      </router-link>
                      <div class="video-channel__stats">
                        {{ video?.subscriptions?.[0]?.total_videos || 0 }} 视频
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  v-if="isVideoChannelVisible && video?.subscriptions?.[0]"
                  class="subscribe-btn"
                  :disabled="isChannelUnsubscribing"
                  :title="isChannelUnsubscribing ? '正在取消订阅' : '取消订阅'"
                  @click.stop="handleUnsubscribe(video.subscriptions[0].id)"
                >
                  <Icon
                    :icon="isChannelUnsubscribing ? 'lucide:loader-circle' : 'lucide:bell-off'"
                    class="subscribe-btn__icon"
                    :class="{ 'is-spinning': isChannelUnsubscribing }"
                  />
                  <span class="subscribe-btn__label">{{ isChannelUnsubscribing ? '取消中' : '取消订阅' }}</span>
                </button>

                <!-- 操作按钮 -->
                <div class="video-meta__actions">
                  <template v-for="action in videoActions" :key="action.key">
                    <button
                      v-if="!action.href"
                      class="action-btn"
                      :class="{ 'is-active': action.active, [`tone-${action.tone}`]: true }"
                      @click="handleVideoAction(action)"
                    >
                      <Icon :icon="action.icon" class="action-btn__icon" />
                      <span class="action-btn__label">{{ action.label }}</span>
                    </button>
                    <a
                      v-else
                      :href="action.href"
                      target="_blank"
                      class="action-btn"
                    >
                      <Icon :icon="action.icon" class="action-btn__icon" />
                      <span class="action-btn__label">{{ action.label }}</span>
                    </a>
                  </template>
                </div>
              </div>
            </div>
            <div v-else class="video-meta-skeleton">
              <div class="skeleton-title w-3/4 h-8 bg-muted rounded"></div>
              <div class="flex items-center justify-between mt-6">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-muted"></div>
                  <div class="space-y-2">
                    <div class="w-24 h-4 bg-muted rounded"></div>
                    <div class="w-16 h-3 bg-muted rounded"></div>
                  </div>
                </div>
                <div class="flex gap-2">
                  <div v-for="i in 4" :key="i" class="w-20 h-8 bg-muted rounded"></div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- 右侧区域 - 相关视频 -->
      <div class="video-aside">
        <div class="video-aside__panel">
          <div class="video-aside__header">
            <div class="video-aside__tabs">
              <button
                class="video-aside__tab"
                :class="{ 'is-active': asideTab === 'related' }"
                @click="asideTab = 'related'"
              >
                相关视频
              </button>
              <button
                class="video-aside__tab"
                :class="{ 'is-active': asideTab === 'clips' }"
                @click="asideTab = 'clips'"
              >
                视频片段
                <span v-if="clipMarkers.length > 0" class="video-aside__tab-badge">{{ clipMarkers.length }}</span>
              </button>
              <button
                class="video-aside__tab"
                :class="{ 'is-active': asideTab === 'playlist' }"
                @click="asideTab = 'playlist'"
              >
                播放列表
                <span v-if="activePlaylistItems.length > 0" class="video-aside__tab-badge">{{ activePlaylistItems.length }}</span>
              </button>
            </div>
          </div>
          <div class="video-aside__content">
            <!-- 相关视频 tab -->
            <Transition v-if="asideTab === 'related'" name="fade-aside" mode="out-in">
              <div v-if="loadingRelated && !relatedVideos.length" key="skeleton" class="related-videos-list">
                <RelatedVideoSkeleton v-for="i in 8" :key="i" :delay="i * 100" />
              </div>
              <div v-else-if="!relatedVideos.length && !loadingRelated" key="empty" class="video-aside__empty">暂无推荐</div>
              <div v-else key="list" class="related-videos-list">
                <TransitionGroup name="related-list">
                  <article
                    v-for="(relatedVideo, index) in relatedVideos"
                    :key="relatedVideo.id"
                    class="related-video-card group"
                    @click="goToVideo(relatedVideo.id, relatedVideo)"
                  >
                    <!-- 保持之前的卡片设计内容不变 -->
                    <div class="related-video-card__thumb-container">
                      <div class="related-video-card__thumb">
                        <img
                          v-if="relatedVideo.thumbnail && !relatedThumbnailErrorIds.has(relatedVideo.id)"
                          :src="relatedVideo.thumbnail"
                          referrerpolicy="no-referrer"
                          class="related-video-card__image"
                          :class="{ 'image-loaded': relatedImagesLoaded[relatedVideo.id] }"
                          draggable="false"
                          :alt="relatedVideo.title"
                          @load="relatedImagesLoaded[relatedVideo.id] = true"
                          @error="() => relatedThumbnailErrorIds.add(relatedVideo.id)"
                        >
                        <div v-else class="related-video-card__fallback">
                          <div class="fallback-noise"></div>
                          <div class="fallback-content">
                            <Icon icon="lucide:image-off" class="fallback-icon" />
                            <span class="fallback-status">暂无封面</span>
                            <span class="fallback-id">ID: {{ formatVideoCardId(relatedVideo.id) }}</span>
                          </div>
                        </div>
                        <div class="related-video-card__scanline"></div>
                        
                        <div class="related-video-card__duration">
                          {{ formatDuration(relatedVideo.duration) }}
                        </div>
                      </div>
                    </div>

                    <div class="related-video-card__body">
                      <div class="related-video-card__title">
                        {{ relatedVideo.title }}
                      </div>
                      <div class="related-video-card__meta">
                        <SubscriptionAvatar
                          v-if="relatedVideo.subscriptions?.[0]"
                          :src="relatedVideo.subscriptions[0].avatar"
                          :name="relatedVideo.subscriptions[0].name"
                          size="sm"
                          class="related-video-card__avatar"
                        />
                        <router-link
                          v-if="relatedVideo.subscriptions?.[0]?.id"
                          :to="`/subscription/${relatedVideo.subscriptions[0].id}/all`"
                          @click.stop
                          class="related-video-card__channel"
                        >
                          {{ relatedVideo.subscriptions[0].name }}
                        </router-link>
                        <span v-else class="related-video-card__site">
                          {{ relatedVideo.site }}
                        </span>
                        <span class="related-video-card__separator">/</span>
                        <span v-if="relatedVideo.uploaded_at" class="related-video-card__date">
                          {{ formatDate(relatedVideo.uploaded_at) }}
                        </span>
                      </div>
                    </div>
                  </article>
                </TransitionGroup>
              </div>
            </Transition>
            <!-- 视频片段 tab -->
            <Transition v-else-if="asideTab === 'clips'" name="fade-aside" mode="out-in">
              <div v-if="!clipMarkers.length" key="empty" class="clip-empty">
                <div class="clip-empty__icon">
                  <Icon icon="lucide:scissors" />
                </div>
                <div class="clip-empty__text">Shift + M</div>
              </div>
              <div v-else key="list" class="clip-markers-list">
                <div
                  v-for="marker in clipMarkers"
                  :key="marker.id"
                  class="clip-row"
                  :class="{ 'is-active': isClipActive(marker) }"
                  @click="handleClipRowClick(marker)"
                >
                  <div class="clip-row__thumb">
                    <img
                      v-if="marker.preview_image_url"
                      :src="marker.preview_image_url"
                      class="clip-row__thumb-image"
                      referrerpolicy="no-referrer"
                      draggable="false"
                      :alt="marker.title || 'preview'"
                    >
                    <div v-else class="clip-row__thumb-fallback">
                      <div class="fallback-noise"></div>
                    </div>
                  </div>
                  <div class="clip-row__info">
                    <div class="clip-row__title-row">
                      <template v-if="isEditingClipMarker(marker.id)">
                        <input
                        :data-clip-title-input="marker.id"
                        :value="clipMarkerTitleDraft"
                        class="clip-row__title-input"
                        type="text"
                        maxlength="255"
                        placeholder="命名片段"
                        @click.stop
                        @input="clipMarkerTitleDraft = $event.target.value"
                        @keydown.enter.prevent="commitClipMarkerTitle(marker)"
                        @keydown.esc.prevent="cancelClipMarkerTitleEdit()"
                        @blur="commitClipMarkerTitle(marker)"
                        >
                        <button
                        class="clip-row__action"
                        title="保存"
                        :disabled="isSavingClipMarkerTitle"
                        @click.stop="commitClipMarkerTitle(marker)"
                        >
                          <Icon icon="lucide:check" />
                        </button>
                      </template>
                      <template v-else>
                        <span v-if="getClipMarkerTitle(marker)" class="clip-row__title">
                          {{ getClipMarkerTitle(marker) }}
                        </span>
                        <span v-else class="clip-row__title clip-row__title--empty"></span>
                        <button
                        class="clip-row__action"
                        title="命名"
                        @click.stop="startClipMarkerTitleEdit(marker)"
                        >
                          <Icon icon="lucide:pencil-line" />
                        </button>
                      </template>
                    </div>
                    <span class="clip-row__range">
                      {{ formatTime(marker.start_time) }}
                      <template v-if="marker.start_time !== marker.end_time"> → {{ formatTime(marker.end_time) }}</template>
                    </span>
                    <div class="clip-row__progress" v-if="marker.start_time !== marker.end_time">
                      <div
                        class="clip-row__progress-fill"
                        :style="{ width: `${getClipProgress(marker)}%`, background: getMarkerColor(marker) }"
                      ></div>
                    </div>
                  </div>
                  <button
                    class="clip-row__del"
                    @click.stop="handleDeleteMarker(marker.id)"
                    title="delete"
                  >
                    <Icon icon="lucide:x" />
                  </button>
                </div>
              </div>
            </Transition>
            <Transition v-else-if="asideTab === 'playlist'" name="fade-aside" mode="out-in">
              <div key="playlist" class="playlist-aside">
                <div class="playlist-aside__toolbar">
                  <div class="playlist-aside__toolbar-copy">
                    <span class="playlist-aside__toolbar-title">
                      {{ activePlaylist?.name || '播放列表' }}
                    </span>
                    <span class="playlist-aside__toolbar-meta">
                      {{ activePlaylist ? `${activePlaylistItems.length} 个视频` : `${playlists.length} 个列表` }}
                    </span>
                  </div>
                  <button class="playlist-aside__add-btn" @click="handleAddToPlaylist">
                    <Icon icon="lucide:list-plus" />
                    <span>加入</span>
                  </button>
                </div>

                <div v-if="loadingPlaylists && !playlists.length" class="video-aside__empty">
                  加载中
                </div>
                <div v-else-if="!playlists.length" class="playlist-aside__empty">
                  <div class="playlist-aside__empty-title">暂无列表</div>
                  <div class="playlist-aside__empty-desc">新建后可直接加入当前视频。</div>
                  <button class="playlist-aside__empty-action" @click="handleAddToPlaylist">新建</button>
                </div>
                <template v-else>
                  <div v-if="playlists.length > 1" class="playlist-aside__playlist-list">
                    <button
                      v-for="playlist in playlists"
                      :key="playlist.id"
                      class="playlist-aside__playlist-chip"
                      :class="{ 'is-active': activePlaylist && String(activePlaylist.id) === String(playlist.id) }"
                      @click="selectActivePlaylist(playlist.id)"
                    >
                      <span class="playlist-aside__playlist-name">{{ playlist.name }}</span>
                      <span class="playlist-aside__playlist-count">{{ playlist.video_count }}</span>
                    </button>
                  </div>

                  <div v-if="loadingPlaylistItems" class="video-aside__empty">
                    加载中
                  </div>
                  <div v-else-if="!activePlaylist" class="video-aside__empty">
                    选择列表
                  </div>
                  <div v-else-if="!activePlaylistItems.length" class="video-aside__empty">
                    列表为空
                  </div>
                  <div v-else class="playlist-aside__items">
                    <div
                      v-for="(item, index) in activePlaylistItems"
                      :key="item.id"
                      class="playlist-aside__item"
                      :class="{ 'is-active': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                      @click="playPlaylistItem(item)"
                    >
                      <span class="playlist-aside__item-index">{{ index + 1 }}</span>
                      <div class="playlist-aside__item-thumb">
                        <img
                          v-if="item.video?.thumbnail"
                          :src="item.video.thumbnail"
                          referrerpolicy="no-referrer"
                          :alt="item.video.title"
                          @error="handlePlaylistItemImageError"
                        >
                        <div v-else class="playlist-aside__item-thumb-fallback">
                          <Icon icon="lucide:film" />
                        </div>
                      </div>
                      <div class="playlist-aside__item-body">
                        <span class="playlist-aside__item-title">{{ item.video?.title || '未知视频' }}</span>
                        <span class="playlist-aside__item-meta">{{ formatDuration(item.video?.duration) }}</span>
                      </div>
                      <button
                        class="playlist-aside__item-remove"
                        @click.stop="handleRemoveVideoFromActivePlaylist(item)"
                        title="从播放列表移除"
                      >
                        <Icon icon="lucide:x" />
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>

    <Dialog :open="showPlaylistPicker" @update:open="handlePlaylistPickerOpenChange">
      <DialogContent class="playlist-picker-dialog">
        <DialogHeader class="playlist-picker__header">
          <DialogTitle>加入列表</DialogTitle>
        </DialogHeader>

        <div class="playlist-picker__body">
          <div v-if="playlists.length" class="playlist-picker__section">
            <Input v-model="playlistPickerQuery" class="playlist-picker__search" placeholder="搜索列表" />
          </div>

          <div v-if="playlists.length" class="playlist-picker__list">
            <button
              v-for="playlist in filteredPlaylists"
              :key="playlist.id"
              class="playlist-picker__item"
              :disabled="isPlaylistPickerSubmitting"
              @click="handleAddCurrentVideoToPlaylist(playlist.id)"
            >
              <span class="playlist-picker__item-copy">
                <span class="playlist-picker__item-title">{{ playlist.name }}</span>
                <span class="playlist-picker__item-meta">{{ playlist.video_count }} 个视频</span>
              </span>
              <Icon icon="lucide:plus" class="playlist-picker__item-icon" />
            </button>
            <div v-if="playlistPickerQuery.trim() && !filteredPlaylists.length" class="playlist-picker__empty">
              没有结果
            </div>
          </div>
          <div v-else class="playlist-picker__blank">还没有列表</div>

          <div class="playlist-picker__create-row" :class="{ 'is-standalone': !playlists.length }">
            <Input v-model="newPlaylistName" class="playlist-picker__create-input" placeholder="新建列表" />
            <button
              class="playlist-picker__create-btn"
              :disabled="isPlaylistPickerSubmitting || !newPlaylistName.trim()"
              @click="handleCreatePlaylistFromPicker"
            >
              创建
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, watch, computed, reactive, inject } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import usePlaybackOrchestrator from '../composables/usePlaybackOrchestrator';
import usePlaybackReporting from '../composables/usePlaybackReporting';
import useVideoActionBar from '../composables/useVideoActionBar';
import useVideoClipMarkers from '../composables/useVideoClipMarkers';
import useVideoPlaybackShell from '../composables/useVideoPlaybackShell';
import useVideoPageNavigation from '../composables/useVideoPageNavigation';
import useVideoPlaylistPanel from '../composables/useVideoPlaylistPanel';
import { useGlobalVideoPlayer } from '@/composables/useGlobalVideoPlayer'
import { useAppTheme } from '@/composables/useAppTheme'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import RelatedVideoSkeleton from '@/components/video-player/RelatedVideoSkeleton.vue';
import { LocalStorageAdapter } from '@/components/video-player/core';
import { Icon } from '@iconify/vue';
import useVideoHistory from "../composables/useVideoHistory";
import { formatDate, formatDuration, formatTime } from '../utils/dateFormat';
import { formatVideoCardId } from '@/utils/videoCard';
import useVideoInteraction from '../composables/useVideoInteraction';
import usePlaylist from '../composables/usePlaylist';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { unsubscribe as apiUnsubscribe } from '@/api'
import { notifySubscriptionRemoved } from '@/utils/subscriptionEvents'




const route = useRoute();
const router = useRouter();
const emitter = inject('emitter');
const APP_TITLE = 'Squirrel'

const playerAdapter = new LocalStorageAdapter();
const { effectiveTheme } = useAppTheme()
const {
  seekGlobalVideoPlayer,
  playGlobalVideoPlayer,
  activateGlobalVideoPlayerSession,
  clearGlobalVideoPlayerSession,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  globalVideoPlayerSession,
} = useGlobalVideoPlayer()


const {
  video,
  startTime,
  relatedVideos,
  loadingRelated,
  playbackSource,
  subtitleTracks,
  loadAndPlayById,
  externalError,
  isResolvingPlayback,
  hydratePlaybackState,
} = usePlaybackOrchestrator(null);
const { sendReport } = useVideoHistory();
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();
const {
  playlists,
  loading: loadingPlaylists,
  activePlaylist,
  activePlaylistItems,
  currentVideoId,
  loadingItems: loadingPlaylistItems,
  hasPrev,
  hasNext,
  goToPrev,
  goToNext,
  setCurrentVideo,
  fetchPlaylists,
  loadAndSetPlaylist,
  addVideo,
  create: createPlaylist,
  removeVideo,
} = usePlaylist();
const { flushPendingReport, onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate } = usePlaybackReporting(video, sendReport);
const {
  goToVideo,
  hasPrevVideo,
  hasNextVideo,
  handlePrevVideo,
  handleNextVideo,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handleAutoplayNext,
  handlePlayRandom,
} = useVideoPageNavigation({
  route,
  router,
  video,
  relatedVideos,
  goToPrev,
  goToNext,
  onVideoEnded,
})
const asideTab = ref('related')
const {
  showPlaylistPicker,
  playlistPickerQuery,
  newPlaylistName,
  isPlaylistPickerSubmitting,
  filteredPlaylists,
  currentVideoAlreadyInActivePlaylist,
  ensurePlaylistData,
  handlePlaylistPickerOpenChange,
  handleAddToPlaylist,
  selectActivePlaylist,
  handleAddCurrentVideoToPlaylist,
  handleCreatePlaylistFromPicker,
  handleAddCurrentVideoToActivePlaylist,
  playPlaylistItem,
  handleRemoveVideoFromActivePlaylist,
} = useVideoPlaylistPanel({
  video,
  playlists,
  activePlaylist,
  activePlaylistItems,
  fetchPlaylists,
  loadAndSetPlaylist,
  addVideo,
  createPlaylist,
  removeVideo,
  setCurrentVideo,
  goToVideo,
  setAsideTab: (tab) => {
    asideTab.value = tab
  },
})
const {
  videoActions,
  handleVideoAction,
} = useVideoActionBar({
  video,
  interactionTypeLike: INTERACTION_TYPE.LIKE,
  interactionTypeDislike: INTERACTION_TYPE.DISLIKE,
  interactionTypeLater: INTERACTION_TYPE.LATER,
  toggleLike,
  deleteInteraction,
  handleAddToPlaylist,
  handlePlayRandom,
})
const {
  currentPlaybackTime,
  clipMarkers,
  clipMarkerTitleDraft,
  isSavingClipMarkerTitle,
  handlePlaybackTimeUpdate: updateClipPlaybackTime,
  handleClipMarkersUpdated,
  handleClipMarkerSeek,
  handleDeleteMarker,
  getClipMarkerTitle,
  isEditingClipMarker,
  startClipMarkerTitleEdit,
  cancelClipMarkerTitleEdit,
  commitClipMarkerTitle,
  handleClipRowClick,
  getMarkerColor,
  isClipActive,
  getClipProgress,
  formatClipDuration,
} = useVideoClipMarkers({
  video,
  seekToTime: async (time) => {
    const seeked = await seekGlobalVideoPlayer(time)
    if (seeked) {
      await playGlobalVideoPlayer()
    }
    try {
      await focusGlobalVideoPlayer()
    } catch {}
  },
})

const parseSharedStartTime = (value) => {
  if (Array.isArray(value)) {
    return parseSharedStartTime(value[0])
  }

  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return parsed
}

const resolvedInitialTime = computed(() => {
  const sharedStartTime = parseSharedStartTime(route.query.t)
  return sharedStartTime ?? startTime.value
})

const handlePlaybackTimeUpdate = (currentTime) => {
  updateClipPlaybackTime(currentTime)
  onVideoTimeUpdate(currentTime)
}

const handlePlaylistItemImageError = (event) => {
  const target = event?.target
  if (target instanceof HTMLImageElement) {
    target.style.display = 'none'
  }
}

const videoPublishedText = computed(() => {
  const publishedAt = video.value?.publish_date || video.value?.uploaded_at
  return publishedAt ? formatDate(publishedAt) : ''
});


const relatedThumbnailErrorIds = reactive(new Set());
const relatedImagesLoaded = reactive({})
const isVideoChannelVisible = ref(true)
const isChannelUnsubscribing = ref(false)
const videoChannelError = ref('')
const VIDEO_CHANNEL_DISMISS_MS = 180

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const handlePlayerRetry = async () => {
  if (!video.value?.id) return;
  await loadAndPlayById(video.value.id, video.value, { forceRefresh: true });   
};

const {
  videoPlayerHostRef,
  videoPageRef,
  videoSectionRef,
  videoMetaRef,
  isWidescreen,
  toggleWidescreen,
  focusVideoPlayer,
  hasReusableGlobalPlaybackSession,
  hydrateFromGlobalPlaybackSession,
} = useVideoPlaybackShell({
  route,
  emitter,
  playerAdapter,
  video,
  playbackSource,
  subtitleTracks,
  resolvedInitialTime,
  clipMarkers,
  hasPrevVideo,
  hasNextVideo,
  externalError,
  isResolvingPlayback,
  effectiveTheme,
  relatedVideos,
  loadingRelated,
  hasPrev,
  hasNext,
  globalVideoPlayerSession,
  activateGlobalVideoPlayerSession,
  clearGlobalVideoPlayerSession,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  hydratePlaybackState,
  loadAndPlayById,
  onVideoPlay,
  onVideoPause,
  handleAutoplayNext,
  handlePlaybackTimeUpdate,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handlePlayerRetry,
  handleClipMarkerSeek,
  handleClipMarkersUpdated,
  flushPendingReport,
})

const handleUnsubscribe = async (subscriptionId) => {
  if (!subscriptionId || isChannelUnsubscribing.value) return

  isChannelUnsubscribing.value = true
  videoChannelError.value = ''

  const { error } = await apiUnsubscribe(subscriptionId)

  if (error) {
    videoChannelError.value = error?.message || '取消订阅失败'
    isChannelUnsubscribing.value = false
    return
  }

  isVideoChannelVisible.value = false
  notifySubscriptionRemoved(subscriptionId)
  await wait(VIDEO_CHANNEL_DISMISS_MS)
  isChannelUnsubscribing.value = false
};

watch(() => route.params.videoId, (videoId) => {
  setCurrentVideo(videoId ?? null);
}, { immediate: true });

watch(asideTab, async (tab) => {
  if (tab !== 'playlist') return;
  await ensurePlaylistData();
});

watch(
  () => route.query.t,
  async (nextValue, previousValue) => {
    if (nextValue === previousValue) return

    const nextTime = parseSharedStartTime(nextValue)
    if (nextTime === null) return

    await handleClipMarkerSeek(nextTime)
  }
)

watch(() => video.value?.id, () => {
  isVideoChannelVisible.value = true
  isChannelUnsubscribing.value = false
  videoChannelError.value = ''
  currentPlaybackTime.value = resolvedInitialTime.value || 0
})

watch(
  () => [route.params.videoId, video.value?.title],
  ([videoId, videoTitle]) => {
    const resolvedTitle = String(videoTitle || '').trim()
    if (resolvedTitle) {
      document.title = `${resolvedTitle} - ${APP_TITLE}`
      return
    }

    const fallbackId = String(videoId || '').trim()
    document.title = `${fallbackId ? `视频 ${fallbackId}` : '视频播放'} - ${APP_TITLE}`
  },
  { immediate: true }
)

watch(() => relatedVideos.value, () => {
  Object.keys(relatedImagesLoaded).forEach(key => delete relatedImagesLoaded[key])
}, { deep: true })

</script>

<style scoped>
/* 基础容器 */
.terminal-viewport {
  background-color: hsl(var(--background));
  background-image: 
    linear-gradient(hsl(var(--foreground) / 0.02) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--foreground) / 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
  color: hsl(var(--foreground) / 0.8);
}

.video-page {
  min-height: 100%;
}

.video-page__container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  padding: 1rem;
}

@media (min-width: 640px) {
  .video-page__container {
    padding: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .video-page__container {
    padding: 2rem;
  }
}

@media (min-width: 1280px) {
  .video-page__container {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 400px;
    align-items: start;
  }
}

.video-main {
  width: 100%;
  min-width: 0;
}

.video-section {
  width: 100%;
  background: #000;
  border-radius: 0;
  overflow: hidden;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
}

.video-player-host {
  position: absolute;
  inset: 0;
}

/* 推荐视频列表项 - 彻底移除卡片效果 */
.related-video-card {
  position: relative;
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.65rem;
  padding: 0.4rem 0;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0.1, 1);
  align-items: flex-start;
}

@media (max-width: 640px) {
  .related-video-card {
    grid-template-columns: 110px 1fr;
    gap: 0.5rem;
  }
}

.related-video-card:hover {
  transform: translateX(4px);
  background: hsl(var(--foreground) / 0.03) !important;
}

.related-video-card__thumb-container {
  width: 100%;
}

.related-video-card__thumb {
  position: relative;
  overflow: hidden;
  border-radius: 4px; /* 进一步减小圆角，更显精致 */
  background: hsl(var(--background));
  aspect-ratio: 16 / 9;
  width: 100%;
}

.related-video-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.related-video-card__image.image-loaded {
  opacity: 1;
}

.related-video-card__fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    radial-gradient(circle at 32% 24%, hsl(var(--primary) / 0.14), transparent 34%),
    linear-gradient(135deg, hsl(var(--muted) / 0.68), hsl(var(--background)));
  color: hsl(var(--muted-foreground));
}

.related-video-card__fallback .fallback-noise {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
  opacity: 0.045;
}

.related-video-card__fallback .fallback-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.related-video-card__fallback .fallback-icon {
  width: 1.1rem;
  height: 1.1rem;
  color: hsl(var(--primary) / 0.72);
}

.related-video-card__fallback .fallback-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  font-weight: 700;
  color: hsl(var(--foreground) / 0.66);
  line-height: 1;
}

.related-video-card__fallback .fallback-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.62);
  line-height: 1;
}

.related-video-card__title {
  font-size: 0.82rem; /* 稍微调小字号 */
  font-weight: 600;
  line-height: 1.3;
  color: hsl(var(--foreground));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 0.2rem;
  transition: color 0.2s;
}

.related-video-card:hover .related-video-card__title {
  color: hsl(var(--primary));
}

.related-video-card__meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem; /* 稍微调小字号 */
  color: hsl(var(--muted-foreground) / 0.8);
}

.related-video-card__avatar {
  width: 1.1rem !important;
  height: 1.1rem !important;
  border-radius: calc(var(--radius-sm) - 1px);
  flex-shrink: 0;
}

.related-video-card__channel {
  max-width: 6rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.related-video-card__duration {
  position: absolute;
  right: 0.25rem;
  bottom: 0.25rem;
  padding: 0.05rem 0.25rem;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 0.65rem;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
}

/* 宽屏/剧院模式适配 - 优化可视区域 */
.video-page__container.is-widescreen {
  --video-theater-top-offset: calc(var(--app-topbar-height, 0px) + 0.5rem);
  /* 增加保底高度，从 8.5rem 提升到更安全的 11rem，确保标题+两行信息可见 */
  --video-theater-meta-peek: clamp(10rem, 20vh, 14rem); 
  --video-theater-bottom-gap: 0.5rem;
  --video-theater-max-height: calc(100vh - var(--video-theater-top-offset) - var(--video-theater-meta-peek) - var(--video-theater-bottom-gap));
  --video-theater-max-height: calc(100dvh - var(--video-theater-top-offset) - var(--video-theater-meta-peek) - var(--video-theater-bottom-gap));
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  max-width: none;
  width: 100%;
}

.video-page__container.is-widescreen .video-section {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100vw;
  height: var(--video-theater-max-height);
  margin-inline: calc(50% - 50vw);
  background: #000;
  overflow: hidden; /* 防止溢出 */
}

/* 关键修复：确保容器在高度受限时也能完整显示 */
.video-page__container.is-widescreen .video-container {
  height: 100%;
  width: 100%;
  max-height: var(--video-theater-max-height);
  aspect-ratio: 16 / 9;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-page__container.is-widescreen .video-container :deep(.sp-player) {
  height: 100%;
  width: 100%;
  max-height: 100%;
}

/* 宽屏模式下信息区域适配 */
.video-page__container.is-widescreen .video-meta {
  margin-top: 0.75rem;
}

.video-page__container.is-widescreen .video-meta__headline {
  margin-bottom: 0.5rem;
}

.video-page__container.is-widescreen .video-meta__title {
  font-size: 1rem;
}

.video-page__container.is-widescreen .video-meta__publish-date {
  margin-top: 0.1rem;
  font-size: 0.66rem;
}

.video-page__container.is-widescreen .video-meta__info-row {
  gap: 0.375rem;
}

.video-page__container.is-widescreen .video-channel__avatar {
  width: 2rem !important;
  height: 2rem !important;
}

.video-page__container.is-widescreen .video-channel__name {
  font-size: 0.85rem;
}

.video-page__container.is-widescreen .video-channel__stats {
  font-size: 0.65rem;
}

.video-page__container.is-widescreen .subscribe-btn {
  padding: 0.3rem 0.75rem;
  font-size: 0.7rem;
}

.video-page__container.is-widescreen .subscribe-btn__icon {
  width: 12px;
  height: 12px;
}

.video-page__container.is-widescreen .video-meta__divider {
  height: 20px;
  margin: 0 0.125rem;
}

.video-page__container.is-widescreen .action-btn {
  padding: 0.3rem 0.6rem;
  font-size: 0.7rem;
  gap: 0.2rem;
}

.video-page__container.is-widescreen .action-btn__icon {
  width: 14px;
  height: 14px;
}

.video-aside {
  min-height: 0;
}

.video-aside__panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: calc(100vh - var(--app-topbar-height, 0px) - 2rem);
  max-height: calc(100dvh - var(--app-topbar-height, 0px) - 2rem);
  overflow: hidden;
}

.video-aside__header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  margin-bottom: 1rem;
}

.video-page__container.is-widescreen .video-aside {
  position: static;
  top: auto;
  margin-top: 1rem;
}

.video-aside__content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.video-aside__content::-webkit-scrollbar {
  display: none;
}

/* 侧边栏整体样式 */
.video-aside__header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 1rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  margin-bottom: 0;
}

.video-aside__tabs {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  gap: 0.25rem;
  background: hsl(var(--background));
  padding: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.video-aside__tab {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.video-aside__tab:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.1);
}

.video-aside__tab.is-active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.08);
  border-color: hsl(var(--primary) / 0.2);
}

.video-aside__tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.25rem;
  font-size: 0.6rem;
  font-weight: 700;
  color: hsl(var(--primary-foreground));
  background: hsl(var(--primary));
  border-radius: 9999px;
  line-height: 1;
}

.video-aside__empty {
  text-align: center;
  color: hsl(var(--muted-foreground));
  font-size: 0.8rem;
  padding: 2rem 0;
}

.clip-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1rem;
  text-align: center;
  gap: 0.5rem;
}

.clip-empty__icon {
  color: hsl(var(--muted-foreground) / 0.3);
  font-size: 1.5rem;
}

.clip-empty__text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  letter-spacing: 0.1em;
}

.clip-markers-list {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.clip-row {
  display: grid;
  grid-template-columns: 6.25rem minmax(0, 1fr) 1.5rem;
  align-items: center;
  gap: 0.75rem;
  padding: 0.35rem 0;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0.1, 1);
}

.clip-row:hover {
  transform: translateX(4px);
}

.clip-row:hover .clip-row__del {
  opacity: 1;
}

.clip-row.is-active .clip-row__range {
  color: hsl(var(--foreground));
  font-weight: 600;
}

.clip-row__thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 3px;
  overflow: hidden;
  background: hsl(var(--secondary));
  border: 1px solid hsl(var(--border) / 0.4);
  transition: all 0.2s;
}

.clip-row:hover .clip-row__thumb {
  border-color: hsl(var(--primary) / 0.4);
  box-shadow: inset 0 0 10px hsl(var(--primary) / 0.1);
}

.clip-row__thumb-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.clip-row__thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.clip-row__info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.clip-row__title-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
  min-height: 1.4rem;
}

.clip-row__title {
  min-width: 0;
  flex: 1;
  font-size: 0.76rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.clip-row__title--empty {
  min-height: 1rem;
}

.clip-row__title-input {
  min-width: 0;
  flex: 1;
  height: 1.6rem;
  padding: 0 0.45rem;
  border-radius: 4px;
  border: 1px solid hsl(var(--primary) / 0.35);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.74rem;
  outline: none;
}

.clip-row__title-input:focus {
  border-color: hsl(var(--primary) / 0.6);
  box-shadow: 0 0 0 1px hsl(var(--primary) / 0.2);
}

.clip-row__range {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: hsl(var(--muted-foreground));
  transition: color 0.2s;
}

.clip-row__progress {
  height: 1px;
  background: hsl(var(--accent) / 0.2);
  border-radius: 1px;
  overflow: hidden;
}

.clip-row__progress-fill {
  height: 100%;
  border-radius: 1px;
  transition: width 0.5s linear;
}

.clip-row__del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s;
}

.clip-row__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s;
  flex-shrink: 0;
}

.clip-row__del:hover {
  color: hsl(var(--destructive));
  background: hsl(var(--destructive) / 0.1);
}

.clip-row:hover .clip-row__action,
.clip-row__action:focus-visible,
.clip-row__action:disabled {
  opacity: 1;
}

.clip-row__action:hover:not(:disabled) {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.clip-row__action:disabled {
  cursor: not-allowed;
}

.playlist-aside {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.playlist-aside__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.playlist-aside__toolbar-copy {
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
  min-width: 0;
}

.playlist-aside__toolbar-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-aside__toolbar-meta {
  font-size: 0.68rem;
  color: hsl(var(--muted-foreground));
}

.playlist-aside__add-btn,
.playlist-aside__empty-action,
.playlist-picker__create-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--primary) / 0.35);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.playlist-aside__add-btn,
.playlist-aside__empty-action {
  padding: 0.38rem 0.78rem;
}

.playlist-aside__add-btn:hover,
.playlist-aside__empty-action:hover,
.playlist-picker__create-btn:hover:not(:disabled) {
  background: hsl(var(--primary) / 0.16);
  border-color: hsl(var(--primary) / 0.55);
}

.playlist-aside__playlist-list {
  display: flex;
  gap: 0.45rem;
  overflow-x: auto;
  padding-bottom: 0.2rem;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.playlist-aside__playlist-list::-webkit-scrollbar {
  display: none;
}

.playlist-aside__playlist-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  max-width: 100%;
  padding: 0.42rem 0.68rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border) / 0.55);
  background: hsl(var(--accent) / 0.06);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.playlist-aside__playlist-chip:hover {
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
  background: hsl(var(--accent) / 0.12);
}

.playlist-aside__playlist-chip.is-active {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.35);
  background: hsl(var(--primary) / 0.08);
}

.playlist-aside__playlist-name {
  max-width: 9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.74rem;
  font-weight: 600;
}

.playlist-aside__playlist-count {
  min-width: 1.15rem;
  height: 1.15rem;
  padding: 0 0.28rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: hsl(var(--background) / 0.9);
  font-size: 0.62rem;
  font-family: 'JetBrains Mono', monospace;
}

.playlist-aside__items {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.playlist-aside__item {
  display: grid;
  grid-template-columns: 1.6rem 5rem minmax(0, 1fr) 1.5rem;
  gap: 0.55rem;
  align-items: center;
  padding: 0.45rem 0.5rem;
  border-radius: 8px;
  background: hsl(var(--accent) / 0.04);
  border: 1px solid hsl(var(--border) / 0.4);
  cursor: pointer;
  transition: all 0.15s ease;
}

.playlist-aside__item:hover {
  background: hsl(var(--accent) / 0.08);
  border-color: hsl(var(--border) / 0.65);
}

.playlist-aside__item.is-active {
  background: hsl(var(--primary) / 0.08);
  border-color: hsl(var(--primary) / 0.28);
}

.playlist-aside__item-index {
  font-size: 0.68rem;
  font-family: 'JetBrains Mono', monospace;
  color: hsl(var(--muted-foreground));
  text-align: center;
}

.playlist-aside__item-thumb {
  width: 5rem;
  aspect-ratio: 16 / 9;
  border-radius: 5px;
  overflow: hidden;
  background: hsl(var(--muted));
}

.playlist-aside__item-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.playlist-aside__item-thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.playlist-aside__item-body {
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
  min-width: 0;
}

.playlist-aside__item-title {
  font-size: 0.78rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.playlist-aside__item-meta {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground));
  font-family: 'JetBrains Mono', monospace;
}

.playlist-aside__item-remove {
  width: 1.5rem;
  height: 1.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  opacity: 0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.playlist-aside__item:hover .playlist-aside__item-remove {
  opacity: 1;
}

.playlist-aside__item-remove:hover {
  color: hsl(var(--destructive));
  background: hsl(var(--destructive) / 0.1);
}

.playlist-aside__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  padding: 2.25rem 1rem;
  text-align: center;
}

.playlist-aside__empty-title {
  font-size: 0.84rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.playlist-aside__empty-desc {
  font-size: 0.72rem;
  line-height: 1.5;
  color: hsl(var(--muted-foreground));
  max-width: 18rem;
}

.playlist-picker-dialog {
  max-width: 28rem;
  gap: 0;
  overflow: hidden;
  padding: 0;
}

.playlist-picker__header {
  padding: 1.1rem 1.1rem 0.55rem;
}

.playlist-picker__body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0 1.1rem 1.1rem;
}

.playlist-picker__section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.playlist-picker__list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: 14rem;
  overflow-y: auto;
  padding-right: 0.2rem;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.playlist-picker__list::-webkit-scrollbar {
  display: none;
}

.playlist-picker__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.85rem;
  border-radius: 10px;
  border: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--accent) / 0.05);
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.playlist-picker__item:hover:not(:disabled) {
  border-color: hsl(var(--primary) / 0.35);
  background: hsl(var(--primary) / 0.06);
}

.playlist-picker__item:disabled,
.playlist-picker__create-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.playlist-picker__item-copy {
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
  min-width: 0;
}

.playlist-picker__item-title {
  font-size: 0.82rem;
  font-weight: 600;
}

.playlist-picker__item-meta {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

.playlist-picker__item-icon {
  flex-shrink: 0;
  color: hsl(var(--primary));
}

.playlist-picker__empty {
  padding: 0.9rem 0.5rem;
  text-align: center;
  font-size: 0.78rem;
  color: hsl(var(--muted-foreground));
}

.playlist-picker__blank {
  padding: 1rem 0.35rem 0.15rem;
  text-align: center;
  font-size: 0.8rem;
  color: hsl(var(--muted-foreground));
}

.playlist-picker__create-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.55rem;
  align-items: center;
  padding-top: 0.8rem;
  border-top: 1px solid hsl(var(--border) / 0.45);
}

.playlist-picker__create-row.is-standalone {
  padding-top: 0;
  border-top: none;
}

.playlist-picker__create-btn {
  padding: 0.48rem 0.85rem;
}

.video-aside__title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.video-aside__status {
  font-size: 0.7rem;
  color: hsl(var(--primary) / 0.6);
  font-family: 'JetBrains Mono', monospace;
}

.related-videos-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* 视频元数据区域 */
.video-meta {
  margin-top: 0.875rem;
}

.video-meta__headline {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.video-meta__title {
  font-size: clamp(1rem, 1rem + 0.3rem, 1.2rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.4;
  word-break: break-word;
  color: hsl(var(--foreground));
  margin: 0;
}

.video-meta__publish-date {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  line-height: 1.2;
  white-space: nowrap;
}

.video-meta__publish-date-icon {
  width: 0.88rem;
  height: 0.88rem;
  flex-shrink: 0;
}

/* 信息行：频道 + 操作按钮 */
.video-meta__info-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 频道信息 */
.video-channel {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.video-channel__primary {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.video-channel__avatar-wrapper {
  flex-shrink: 0;
}

.video-channel__avatar {
  width: 2.5rem !important;
  height: 2.5rem !important;
  border-radius: calc(var(--radius-sm) - 1px);
  border: 2px solid hsl(var(--border));
}

.video-channel__identity {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.video-channel__name {
  font-size: 0.9rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.video-channel__name:hover {
  color: hsl(var(--primary));
}

.video-channel__stats {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

/* 订阅按钮 */
.subscribe-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.875rem;
  border-radius: 20px;
  background: hsl(var(--secondary) / 0.6);
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid hsl(var(--border) / 0.65);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.subscribe-btn:hover {
  background: hsl(var(--destructive) / 0.1);
  border-color: hsl(var(--destructive) / 0.35);
  color: hsl(var(--destructive));
}

.subscribe-btn:disabled {
  cursor: wait;
  opacity: 0.75;
}

.subscribe-btn__icon {
  width: 14px;
  height: 14px;
}

.subscribe-btn__icon.is-spinning {
  animation: spin 0.8s linear infinite;
}

/* 操作按钮 - 靠右 */
.video-meta__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: auto;
  flex-wrap: nowrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.75rem;
  border-radius: 20px;
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground) / 0.7);
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid hsl(var(--border) / 0.4);
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  flex-shrink: 0;
}

.action-btn:hover {
  background: hsl(var(--accent) / 0.2);
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
}

.action-btn.is-active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.4);
}

.action-btn__icon {
  width: 16px;
  height: 16px;
  opacity: 0.8;
}

.action-btn.is-active .action-btn__icon {
  opacity: 1;
}

.action-btn.tone-danger.is-active {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
  border-color: hsl(var(--destructive) / 0.4);
}

.action-btn.tone-later.is-active {
  background:
    linear-gradient(
      135deg,
      hsl(var(--primary) / 0.18),
      hsl(var(--accent) / 0.18)
    );
  color: hsl(var(--foreground));
  border-color: hsl(var(--primary) / 0.45);
  box-shadow:
    0 0 0 1px hsl(var(--primary) / 0.14),
    0 10px 24px hsl(var(--surface-shadow));
}

.action-btn.tone-later.is-active .action-btn__icon {
  color: hsl(var(--primary));
}

/* 响应式适配 */
@media (max-width: 640px) {
  .video-meta__headline {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.35rem;
  }

  .video-meta__publish-date {
    margin-top: 0;
  }

  .video-channel__avatar {
    width: 2.25rem !important;
    height: 2.25rem !important;
  }

  .video-channel__name {
    font-size: 0.85rem;
  }

  .action-btn {
    padding: 0.35rem 0.6rem;
    font-size: 0.7rem;
    gap: 0.25rem;
  }

  .action-btn__icon {
    width: 14px;
    height: 14px;
  }
}

/* 过渡动画 */
.fade-player-enter-active {
  transition: opacity 0.5s ease;
}
.fade-player-enter-from {
  opacity: 0;
}

.related-list-enter-active {
  transition: all 0.3s ease;
}
.related-list-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
</style>
