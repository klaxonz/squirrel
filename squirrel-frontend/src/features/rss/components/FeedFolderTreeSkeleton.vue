<template>
  <div
    class="feed-folder-tree-skeleton"
    role="status"
    aria-label="正在加载订阅源"
  >
    <div
      v-for="(group, groupIndex) in skeletonGroups"
      :key="groupIndex"
      class="feed-folder-tree-skeleton__group"
    >
      <div class="feed-folder-tree-skeleton__folder">
        <div class="feed-folder-tree-skeleton__folder-copy">
          <AppSkeleton
            width="0.75rem"
            height="0.75rem"
            rounded="var(--radius-sm)"
            shimmer
          />
          <AppSkeleton
            :width="group.folderWidth"
            height="0.6875rem"
            rounded="var(--radius-sm)"
            shimmer
          />
        </div>
        <AppSkeleton
          width="1rem"
          height="0.625rem"
          rounded="var(--radius-sm)"
          shimmer
        />
      </div>

      <div class="feed-folder-tree-skeleton__feeds">
        <div
          v-for="(feedWidth, feedIndex) in group.feedWidths"
          :key="feedIndex"
          class="feed-folder-tree-skeleton__feed"
        >
          <AppSkeleton
            width="1rem"
            height="1rem"
            rounded="var(--radius-sm)"
            shimmer
          />
          <AppSkeleton
            :width="feedWidth"
            height="0.6875rem"
            rounded="var(--radius-sm)"
            shimmer
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSkeleton from '@/shared/components/AppSkeleton.vue'

const skeletonGroups = [
  {
    folderWidth: '38%',
    feedWidths: ['68%', '54%', '62%'],
  },
  {
    folderWidth: '48%',
    feedWidths: ['58%', '72%'],
  },
  {
    folderWidth: '32%',
    feedWidths: ['64%', '50%'],
  },
] as const
</script>

<style scoped>
.feed-folder-tree-skeleton,
.feed-folder-tree-skeleton__group,
.feed-folder-tree-skeleton__feeds {
  display: flex;
  flex-direction: column;
}

.feed-folder-tree-skeleton,
.feed-folder-tree-skeleton__group {
  gap: 0.125rem;
}

.feed-folder-tree-skeleton__folder,
.feed-folder-tree-skeleton__folder-copy,
.feed-folder-tree-skeleton__feed {
  display: flex;
  align-items: center;
}

.feed-folder-tree-skeleton__folder {
  justify-content: space-between;
  min-height: 2rem;
  padding: 0.25rem 0.625rem;
}

.feed-folder-tree-skeleton__folder-copy {
  min-width: 0;
  flex: 1 1 auto;
  gap: 0.375rem;
}

.feed-folder-tree-skeleton__feeds {
  gap: 0.125rem;
  padding: 0.125rem 0 0.25rem 0.75rem;
}

.feed-folder-tree-skeleton__feed {
  min-height: 2.125rem;
  gap: 0.625rem;
  padding: 0 0.5rem 0 0.75rem;
}
</style>
