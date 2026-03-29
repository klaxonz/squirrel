# History Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the history page to use a list-based layout with date grouping, search, and individual item deletion.

**Architecture:** 
- Create a new `HistoryItem.vue` component for the list view.
- Update `History.vue` to manage state (search, grouping) and handle user interactions.
- Use date-based grouping logic to organize the history timeline.

**Tech Stack:** Vue 3, Tailwind CSS, Lucide Icons (or Heroicons), Shadcn Vue.

---

### Task 1: Create `HistoryItem.vue` Component

**Files:**
- Create: `squirrel-frontend/src/components/history/HistoryItem.vue`

**Step 1: Write minimal implementation**

```vue
<template>
  <div class="history-item flex items-center gap-4 p-3 hover:bg-accent/50 rounded-lg group transition-colors cursor-pointer" @click="$emit('open', video)">
    <div class="thumbnail-container relative w-40 aspect-video flex-shrink-0 bg-black rounded overflow-hidden">
      <img :src="video.thumbnail" referrerpolicy="no-referrer" class="w-full h-full object-cover" />
      <div class="absolute bottom-1 right-1 px-1 py-0.5 bg-black/80 text-[10px] text-white rounded font-mono">
        {{ formatDuration(video.duration) }}
      </div>
      <div v-if="video.progress > 0" class="absolute bottom-0 left-0 h-0.5 bg-primary" :style="{ width: `${video.progress * 100}%` }"></div>
    </div>
    
    <div class="info-container flex-grow min-w-0">
      <h4 class="text-sm font-medium line-clamp-1 mb-1">{{ video.title }}</h4>
      <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <span class="font-mono text-[10px] bg-accent px-1 rounded">{{ video.site_name || 'UNKNOWN' }}</span>
        <span>•</span>
        <span>已看 {{ (video.progress * 100).toFixed(0) }}%</span>
        <span>•</span>
        <span>{{ formatDate(video.updated_at) }}</span>
      </div>
    </div>

    <div class="actions-container opacity-0 group-hover:opacity-100 transition-opacity">
      <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10" @click.stop="$emit('delete', video.id)">
        <TrashIcon class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>

<script setup>
import { TrashIcon } from '@heroicons/vue/24/outline'
import { Button } from '@/components/ui/button'
import { formatDate, formatDuration } from '@/utils/dateFormat'

defineProps({
  video: { type: Object, required: true }
})

defineEmits(['open', 'delete'])
</script>
```

**Step 2: Commit**

```bash
git add squirrel-frontend/src/components/history/HistoryItem.vue
git commit -m "feat(history): add HistoryItem component for list view"
```

---

### Task 2: Update `History.vue` with Search and Grouping

**Files:**
- Modify: `squirrel-frontend/src/views/History.vue`

**Step 1: Add Search and Grouping Logic**

- Add `searchQuery` ref.
- Add `groupedVideos` computed property.
- Update `processedVideos` to include `site_name` and `updated_at`.
- Implement `handleDelete` function.

**Step 2: Update Template**

- Replace `VideoList` with a custom list implementation using `HistoryItem`.
- Add date headers for groups.
- Update `FeedToolbar` to include a search input (or add it manually if `FeedToolbar` doesn't support it).

**Step 3: Commit**

```bash
git add squirrel-frontend/src/views/History.vue
git commit -m "feat(history): implement date grouping and search in history page"
```

---

### Task 3: Refine Layout and Styling

**Files:**
- Modify: `squirrel-frontend/src/views/History.vue`
- Modify: `squirrel-frontend/src/components/history/HistoryItem.vue`

**Step 1: Improve Date Headers**

- Make headers sticky.
- Add "Today", "Yesterday" labels.

**Step 2: Add Empty State for Search**

- Show a specific message when search returns no results.

**Step 3: Commit**

```bash
git commit -m "style(history): refine timeline layout and date headers"
```
