# Design Doc: History Page Redesign

## Goal
Redesign the history playback page to improve usability, aesthetics, and functionality.

## Key Features
1.  **Modern Timeline Layout**: Organize history records by date (Today, Yesterday, Earlier).
2.  **List-Style View**: Switch from a grid to a detailed list view for better information density and readability.
3.  **Search Functionality**: Real-time search by video title within the history.
4.  **Individual Item Management**: Allow users to delete specific history items.
5.  **Enhanced Metadata**: Show progress percentage, last watch time, and site source clearly.

## Components
### 1. `HistoryItem.vue`
- **Layout**: Horizontal layout.
- **Left**: Thumbnail with a 16:9 aspect ratio, showing duration and a thin progress bar.
- **Right**: Title, site name (with icon/avatar), last watch time, and progress percentage.
- **Actions**: "Delete" button (trash icon) visible on hover or in a menu.

### 2. `HistoryGroup.vue` (Optional, can be inline)
- A header component for date groups (e.g., "Today", "2023-10-25").

### 3. `History.vue` (Main View)
- **State**:
    - `searchQuery`: For filtering items.
    - `groupedVideos`: Computed property or reactive state that groups `videos` by date.
- **Logic**:
    - Fetch history via `useVideoHistory`.
    - Group items by date (using `last_watch_time` or `updated_at`).
    - Filter items by `searchQuery`.
    - Handle individual deletion via `clearHistory([id])`.

## Data Flow
1.  `History.vue` calls `getWatchHistory` on mount and on scroll.
2.  New items are appended to the `videos` array.
3.  A computed property `groupedVideos` groups the `videos` by date and applies the search filter.
4.  The template iterates over `groupedVideos` and renders date headers and `HistoryItem` components.

## UI/UX Details
- **Empty State**: A modern, clean empty state when no history matches or exists.
- **Loading State**: Shimmer effect for list items.
- **Responsive**: List items should adapt to narrower screens (stacking or shrinking metadata).

## Verification
- Verify date grouping works across page loads.
- Verify search filter works correctly.
- Verify individual deletion removes the item from the list and the backend.
- Verify "Clear History" still works for all items.
