<template>
  <div class="music-comments-panel">
    <div v-if="loading" class="music-comments-state">
      <AppIcon name="loadingSpinner" class="h-6 w-6 animate-spin" />
      <span>评论加载中...</span>
    </div>
    <div v-else-if="error" class="music-comments-state text-destructive">
      <span>{{ error }}</span>
    </div>
    <div v-else-if="!comments.length" class="music-comments-state">
      <AppIcon name="messageCircle" class="h-6 w-6" />
      <span>暂无评论</span>
    </div>
    <div v-else class="music-comments-scrollable">
      <div v-for="comment in comments" :key="comment.id" class="music-comment">
        <div class="music-comment-avatar">
          <img v-if="comment.user_avatar" :src="comment.user_avatar" alt="" />
          <AppIcon v-else name="user" class="h-4 w-4" />
        </div>
        <div class="music-comment-body">
          <div class="music-comment-header">
            <span class="music-comment-user">{{ comment.user_name || '匿名用户' }}</span>
            <span v-if="comment.created_at" class="music-comment-time">{{ comment.created_at }}</span>
          </div>
          <p class="music-comment-text">{{ comment.content }}</p>
          <div class="music-comment-actions">
            <span class="music-comment-stat">
              <AppIcon name="heart" class="h-3 w-3" />
              {{ comment.like_count || 0 }}
            </span>
            <span v-if="comment.reply_count" class="music-comment-stat">
              <AppIcon name="messageCircle" class="h-3 w-3" />
              {{ comment.reply_count }}
            </span>
          </div>
        </div>
      </div>
      <div v-if="hasMore" class="music-comments-more">
        <button class="music-chip" :disabled="loading" @click="$emit('load-more')">
          加载更多评论
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicComment } from '@/api/music'

defineProps<{
  comments: MusicComment[]
  loading?: boolean
  error?: string
  hasMore?: boolean
}>()

defineEmits<{
  'load-more': []
}>()
</script>

<style scoped>
.music-comments-panel {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  scrollbar-width: none;
}

.music-comments-panel::-webkit-scrollbar {
  display: none;
}

.music-comments-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.75rem;
  color: hsl(var(--foreground) / 0.45);
  font-size: 1rem;
}

.music-comments-scrollable {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.music-comment {
  display: flex;
  gap: 0.625rem;
  align-items: flex-start;
}

.music-comment-avatar {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  background: hsl(var(--muted));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.5);
}

.music-comment-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-comment-body {
  flex: 1;
  min-width: 0;
}

.music-comment-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.music-comment-user {
  font-size: 0.6875rem;
  font-weight: 500;
  color: hsl(var(--foreground) / 0.8);
}

.music-comment-time {
  font-size: 0.5625rem;
  color: hsl(var(--foreground) / 0.35);
}

.music-comment-text {
  font-size: 0.75rem;
  line-height: 1.5;
  color: hsl(var(--foreground) / 0.65);
  word-break: break-word;
}

.music-comment-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.music-comment-stat {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.5625rem;
  color: hsl(var(--foreground) / 0.4);
}

.music-comments-more {
  display: flex;
  justify-content: center;
  padding: 0.5rem 0;
}

.music-chip {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-chip:hover {
  background: hsl(var(--muted));
}

.music-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>