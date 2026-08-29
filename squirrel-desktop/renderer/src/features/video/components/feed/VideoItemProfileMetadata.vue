<template>
  <div :class="grid ? 'video-item__meta' : 'video-item__community'">
    <Button
      v-if="profile"
      variant="ghost"
      class="video-item__profile-action"
      :class="{ 'video-item__profile-action--grid': grid }"
      :aria-label="`查看来源：${names}`"
      data-profile-action
      @click="emit('openProfile', profile)"
    >
      <SubscriptionAvatar
        v-if="showAvatar"
        class="video-item__avatar"
        :src="profile.avatar"
        :name="profile.name"
        :size="grid ? 'md' : 'sm'"
      />
      <span class="video-item__source-name">{{ names }}</span>
    </Button>
    <span v-else class="video-item__source-name">{{ names }}</span>
    <span v-if="dateText" class="video-item__date">{{ dateText }}</span>
    <span v-if="site" class="video-item__site">{{ site }}</span>
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import type { VideoProfile } from '@/features/video/types/video'

withDefaults(defineProps<{
  profile: VideoProfile | null
  names: string
  dateText: string
  site?: string | null
  showAvatar: boolean
  grid?: boolean
}>(), { grid: false })

const emit = defineEmits<{ openProfile: [profile: VideoProfile] }>()
</script>
