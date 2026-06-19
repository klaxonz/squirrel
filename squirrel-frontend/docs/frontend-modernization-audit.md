# Frontend Modernization Audit

Open issues found after `98cf62a6 refactor(frontend): unify UI primitives across all
features`. Many feature modules have not yet followed the shared primitives
introduced in `src/shared/ui/` and `src/shared/components/`. This doc is the
living checklist — mark each item `✅ done` with a short note, or `⏭️ skipped`
with reason.

Status legend: `🔴 open` · `🟡 in progress` · `✅ done` · `⏭️ skipped (reason)`

---

## P0 — Highest UX impact

### P0a — music composables lack try/catch; failures hang loading forever 🔴

`useMusicHome.ts:50-119`, `useMusicDetail.ts:81-262`, `useMusicAuth.ts:67-81`
all follow this broken pattern:

```ts
async function loadBanners() {
  bannerLoading.value = true
  const { data } = await getMusicBanner()   // ← on reject
  bannerLoading.value = false                // ← never runs
  banners.value = data?.items || []
}
```

On rejection the `*Loading` ref sticks at `true` forever → permanent spinner,
no user feedback. Mirror `useMusicAuth.ts:47-65` `loadProfile` (which is
correct): `try { ... } finally { loading = false }`, expose `error` ref.

Files:
- `src/features/music/composables/useMusicHome.ts` (loadBanners/Ranks/Playlists/NewAlbums/NewSongs/AiRecommend/EverydayRecommend/HotSearches)
- `src/features/music/composables/useMusicDetail.ts` (selectPlaylist/UserPlaylist/ArtistDetail/Album/RankAsPlaylist/loadMoreTracks)
- `src/features/music/composables/useMusicAuth.ts` (loadProfileHistory/loadProfileListenRank)

### P0b — Music.vue handlers have no error handling 🔴

`src/features/music/views/Music.vue:510-521, 667-689` — `handleSearch`,
`handlePlayMv`, `handlePlayArtistVideo` await/chain API with no try/catch.
A failed MV fetch leaves the modal open with empty `videoUrl` and no message.

### P0c — History.vue loadData has try/finally but no catch 🔴

`src/features/video/views/History.vue:131-139` — page has empty-state but no
error/retry. Mirror `VideosView.vue:33-39`.

### P0d — `alert()` still used (should be `useToast`) 🔴

`src/features/settings/composables/useLogClipboard.ts:58, 90`:
```ts
navigator.clipboard.writeText(logText).catch(err => {
  Logger.error('Failed to copy log', err)
  alert('复制失败，请手动复制')
})
```
Replace with `useToast().error('复制失败，请手动复制')`.

### P0e — music list components missing loading/empty states 🔴

- `MusicPlaylistGrid.vue:22-41` — no loading branch, no empty state (just `<h3>` while loading/empty)
- `MusicAlbumGrid.vue:5-24` — has `AppBlockLoader`, no empty state
- `MusicTrackList.vue:33-103` — no loading, no empty (used by New Songs/Favorites/AI/daily in `Music.vue:188-229`)
- `MusicHomeView.vue:27-63` — each `MusicSection` only checks `xxxLoading`; empty result renders empty grid silently

Use `AppBlockLoader` + `AppEmptyState` from `shared/components`.

---

## P1 — Hand-rolled implementations bypassing shared primitives

### P1a — hand-rolled Dialog overlays → shared `Dialog` 🔴

Project uses `Dialog`/`DialogContent` in `AddChannelDialog`, `ImportSubscriptionDialog`,
`AccountEditDialog`, `FilterModal`, `MusicCreatePlaylistButton` — but these
still hand-roll `fixed inset-0` overlays (no focus trap, no Esc, no a11y):
- `src/features/settings/components/SiteConfigEditorDialog.vue:2-6`
- `src/features/settings/components/TaskDialog.vue:2-3`
- `src/features/music/components/MusicVideoModal.vue:8, 47-56`
- `src/features/rss/views/RssSources.vue:652-674` (image lightbox)

### P1b — hand-rolled Tabs → shared `Tabs` 🔴

Shared `Tabs` primitive is **never used in feature code**. Migrate:
- `src/features/settings/views/Settings.vue:16-27, 66-170, 249-261` (router-bound; consider route-aware Tabs)
- `src/features/music/components/MusicProfileView.vue:68-116, 241`
- `src/features/music/components/player/MusicImmersivePlayer.vue:108-126, 197`
- `src/features/video/components/feed/FeedToolbar.vue:4-25, 157-211` (pill variant)

### P1c — hand-rolled dropdowns/menus → shared `Select` / `DropdownMenu` 🔴

- `src/features/rss/views/RssSources.vue:541-589` — category picker hand-rolled `v-if` + outside-click; same file's `FeedToolbar` already uses shared `Select`
- `src/features/rss/components/RssArticleContextMenu.vue:6`
- `src/features/rss/components/RssFeedContextMenu.vue:6`
- `src/features/video/components/feed/ContextMenu.vue:3`

### P1d — `<AppIcon name="loadingSpinner" animate-spin>` / `refresh`-as-spinner → `AppSpinner` / `<Button :loading>` 🔴

`AppSpinner.vue` JSDoc says "every loading indicator funnels through here"
but feature code still hand-writes it. Sites:
- music: `GlobalMusicPlayerBar.vue:101`, `MusicGreetingSection.vue:69`, `MusicQrLoginPanel.vue:50`, `MusicBarControls.vue:30`, `MusicImmersivePlayer.vue:90`, `MusicTrackPlayButton.vue:7`
- settings: `Settings.vue:200,204`, `ServerConfig.vue:50`, `SiteRuntimeManager.vue:11,44,52,81,113,117,121,200,208`, `ScheduledTasks.vue:72`, `SecuritySettings.vue:34`
- video/rss: `History.vue:14`, `PlaylistView.vue:56`, `Subscribed.vue:207`, `ChannelHeader.vue:107`, `FeedToolbar.vue:115-119`, `RssSources.vue:54,138,430,642`, `AccountEditDialog.vue:149,168`
- Also: many use `:disabled="loading"` + manual spin icon instead of `<Button :loading>` (auto-disable + spinner). Notably: `SiteRuntimeManager.vue:43,51,112,116,120`, `RssSources.vue:49-63`, `MusicImmersivePlayer.vue:89`, `MusicBarControls.vue:26`, `MusicCommentsPanel.vue:36`, `Settings.vue:108,119,140,163,196,199,203`, `ServerConfig.vue:40,46,112`.

### P1e — raw `<input>` / `<input type="checkbox">` → shared `Input` / `Checkbox` 🔴

- `src/features/auth/views/Login.vue:44, 63, 86` (email/password inputs duplicate the full `Input` class boilerplate; rememberMe checkbox)
- `src/features/auth/views/Register.vue:44, 60, 77`
- `src/features/settings/views/ServerConfig.vue:33-42`
- `src/features/video/components/dialogs/ImportSubscriptionDialog.vue:93-99` (per-row checkbox)

### P1f — raw `<button class="bg-destructive ...">` → `Button variant="destructive"` 🔴

- `src/features/video/components/feed/RemoteSearchResults.vue:15`
- `src/features/video/views/RemoteChannelDetail.vue:7`
- `src/features/video/views/ChannelDetailView.vue:46`

### P1g — accessibility: clickable non-interactive elements 🔴

Click handlers on `<article>`/`<div>`/`<span>` without `role="button"`,
`tabindex="0"`, `@keydown.enter/space`. Compare correct pattern at
`Subscribed.vue:63-71`. Sites (worst first):
- `src/features/music/components/shared/MusicCard.vue:2-8` (propagates to all music grids)
- `src/features/music/components/MusicAlbumGrid.vue:6-11`, `MusicPlaylistGrid.vue:23-28`, `MusicTrackList.vue:42-52`, `MusicSearchView.vue:68-73, 106-111, 129-134`
- `src/features/playback/views/VideoPlay.vue:39, 209`
- `src/features/video/components/feed/VideoItem.vue:2-7, 95`
- `src/features/video/views/Subscribed.vue:135`
- `src/features/music/components/MusicQrLoginPanel.vue:48`

### P1h — accessibility: labels, aria-labels, alt 🔴

- **Unassociated form labels**: `SiteConfigEditorDialog.vue:38,42,46,66,73,75` (label text siblings but no `for`/`id`); `PlaylistView.vue:256,260` (`Input id="name"` but no `<label for>`); search inputs `RssSources.vue:82-86,147-151`, `Subscribed.vue:17-21`.
- **Icon-only buttons with `title` but no `aria-label`**: `RssSources.vue:49-63,132-139,300-306`, `SiteRuntimeManager.vue:72-78,94-100`, `VideoItem.vue:24-46` (also hover-only → keyboard unreachable), `SiteConfigEditorDialog.vue:21-26`, `PlaylistPanel.vue:8`.
- **`alt=""` on content images** (empty alt = decorative only): music cover/avatar — `GlobalMusicPlayerBar.vue:81`, `MusicGreetingSection.vue:6`, `MusicAlbumGrid.vue:13`, `MusicPlaylistGrid.vue:30`, `MusicProfileView.vue:26,133,160`, `Profile.vue:15,98`, etc. Mirror `MusicAlbumDetailView.vue:5` (`:alt="album.name"`).

---

## P2 — Code quality

### P2a — `ScheduledTasks.vue` 6× duplicated `result.error → toast` CRUD handler 🔴

`src/features/settings/views/ScheduledTasks.vue:377-387, 393-402, 404-413, 420-430, 432-441, ...`
All identical shape:
```ts
const r = await apiX()
if (!r.error) { toast.success(...); await refreshData() } else { toast.error(...) }
```
Extract `runMutation(apiCall, successMsg, errorMsg)`.

### P2b — cross-file duplicated logic 🔴

- **Context-menu positioning**: `useRssFeeds.ts:184-202` and `useRssEntries.ts:281-299` byte-identical (`menuWidth=200`, `innerWidth` clamp, `nextTick` bottom-overflow fix) → `useContextMenuPosition`
- **`formatCount` (亿/万)**: `MusicHomeView.vue:114-118`, `MusicArtistDetailView.vue:126-127`, `MusicSearchView.vue:222` → util
- **`document.getElementById('app-main-scroll')`**: `RemoteChannelVideoGrid.vue:111`, `RemoteSearchResults.vue:433`, `VideoList.vue:90`, `RemoteChannelDetail.vue:438` → prop/ref

### P2c — duplicate `.toast-*` transition CSS colliding with shared toast system 🔴

`shared/styles/index.css:233-246` defines `app-toast-enter/leave`. But four
views duplicate `.toast-enter-active/...`:
- `src/features/playback/views/VideoPlay.vue:685-696`
- `src/features/settings/views/ScheduledTasks.vue:524-530`
- `src/features/settings/views/Settings.vue:462-468`
- `src/features/settings/views/SiteRuntimeManager.vue:321-349, 886-893` (last is OAuth prompt — deliberate exception but class name collides; rename)

### P2d — untracked `setTimeout` (no `onUnmounted` cleanup) 🔴

- `src/features/profile/views/Profile.vue:268` (`setTimeout(() => saved.value = false, 3000)`)
- `src/features/settings/views/ScheduledTasks.vue:383` (`setTimeout(refreshData, 800)`)
- `src/features/video/components/dialogs/ImportSubscriptionDialog.vue:393` (`setTimeout(resetState, 200)`)

### P2e — untyped function params (implicit `any`) 🔴

- `ScheduledTasks.vue:326, 372, 389, 415, 501`
- `SiteRuntimeManager.vue:434, 449, 690`
- `LogViewer.vue:323, 362, 372, 384`
- `ImportSubscriptionDialog.vue:396`

(Playback adapter `as any` clusters are documented bridge code — not in scope.)

### P2f — layout / detail 🔴

- **`v-html` misuse**: `RssSources.vue:249` uses `v-html="stripHtmlTags(entry.summary)"` for a plain-text preview — should be `{{ ... }}`. `:388` reader `v-html` is fine (sanitizer) but verify allowlist; replace inline fallback string `'<p class=text-muted-foreground>...'` (unquoted attr) with real `<p v-if>`.
- **Inline `style="..."`**: `video-player/SettingsMenu.vue` 20+ repeated `opacity:0.5` + `width:14px` → extract class; `PlaylistPanel.vue:8`; `VideoPlayer.vue:166`.
- **`AppEmptyState` misuse**: `MusicProfileView.vue:5-16` passes raw error string as `title` — use `icon="warning"` + title "加载失败" + `:copy="error"`.
- **Unbounded `v-for`**: `MusicTrackList.vue:42-103` (load-more grows unbounded; reuse `feed/VirtualList.vue`).
- **Huge components to split**: `VideoPlayer.vue` (2078), `RssSources.vue` (1243), `SiteRuntimeManager.vue` (833), `Music.vue` (689), `Subscribed.vue` (678).
- **Scattered `localStorage`**: `MusicSearchView.vue:186,194`, `SiteRuntimeManager.vue:454,463,466,470,478-480`, `useRssReader.ts:23-24,60,64`, `musicPlayer.ts:208,232,400,434`, `usePlayer.ts:158,167`.

---

## Already clean (no action)

- No Options API, no `@ts-ignore`/`@ts-nocheck`, no stray `console.log`, no `TODO/FIXME`, no commented-out dead code.
- All `addEventListener` paired with `removeEventListener` in `onUnmounted`.
- No hand-rolled `<table>`; no `window.confirm` (ConfirmDialog used correctly).
- Playback adapter `as any` is documented bridge code.

---

## Change log

| Date | Item | Note |
|---|---|---|
| 2026-06-19 | doc created | initial audit |
| 2026-06-19 | P0a ✅ | `useMusicHome`, `useMusicDetail`, `useMusicAuth` — all loaders wrapped in try/finally; errors logged + cleared; `*Loading` refs always reset |
| 2026-06-19 | P0b ✅ | `Music.vue` — `handleSearch`/`handlePlayMv`/`handlePlayArtistVideo`/`handleCollectPlaylist`/`handleSelect*FromTrack` now catch + toast on failure |
| 2026-06-19 | P0c ✅ | `History.vue` — added `loadError` ref + catch; template shows `AppEmptyState` with 重试 button on error |
| 2026-06-19 | P0d ✅ | `useLogClipboard.ts` — both `alert()` replaced with `useToast().error()`; zero `alert()` left in `src/` |
| 2026-06-19 | P0e ✅ | `MusicPlaylistGrid`/`MusicAlbumGrid`/`MusicTrackList` — added `AppBlockLoader` + `AppEmptyState` branches; `MusicHomeView` sections got empty-state fallbacks |
| 2026-06-19 | P1a ✅ | `TaskDialog`, `SiteConfigEditorDialog`, `MusicVideoModal` — migrated from hand-rolled `fixed inset-0` overlays to shared `Dialog`/`DialogContent`/`DialogHeader`/`DialogTitle`/`DialogClose`/`DialogFooter` (gains focus trap, Esc, a11y) |
| 2026-06-19 | P1b ✅ (partial) | `MusicProfileView` — tab strip migrated to shared `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`. `MusicImmersivePlayer` tabs kept as buttons (list/content are non-adjacent + comments tab fires a side-effect) but gained `role="tablist"`/`role="tab"`/`aria-selected` |
| 2026-06-19 | P1c ⏭️ (partial) | RSS context menu (`RssArticleContextMenu`) gained `role="menu"`/`role="menuitem"`/`role="menuitemradio"`/`aria-checked`. Full `DropdownMenu` migration deferred — menus own their positioning + expose `rootRef` for overflow reflow; re-platforming would require rewriting `useRssEntries`/`useRssFeeds` positioning logic. `RssSources` category picker deferred — its inline "新建分类" sub-form doesn't map cleanly to `Select`. |
| 2026-06-19 | P1d ⏭️ deferred | ~25 sites of `<AppIcon name="loadingSpinner" animate-spin>` / `refresh`-as-spinner. Mechanical but each is a visual-regression risk; recommend a dedicated pass with screenshot review. |
| 2026-06-19 | P1e ✅ (partial) | `Login`, `Register` (email/password/nickname), `ServerConfig` (server URL) — raw `<input>` → shared `<Input>`. `Login` rememberMe checkbox + `ImportSubscriptionDialog` per-row checkbox left as-is (low frequency, custom styling). |
| 2026-06-19 | P1f ✅ | `RemoteSearchResults`, `RemoteChannelDetail`, `ChannelDetailView` — raw destructive `<button>` → `<Button variant="destructive">` |
| 2026-06-19 | P1g ✅ | `MusicCard` (propagates to all music grids), `VideoItem` — added `role="button"` + `tabindex="0"` + `@keydown.enter/space` |
| 2026-06-19 | P1h ✅ | Content images in `Profile` (×2), `GlobalMusicPlayerBar`, `MusicGreetingSection`, `MusicRecentSection`, `MusicRankGrid` (×2), `MusicProfileView` — `alt=""` → meaningful `:alt`. `MusicImmersivePlayer` cover fixed too. |
| 2026-06-19 | P2a ⏭️ deferred | `ScheduledTasks` 6× duplicated CRUD handler — extract `runMutation`. Safe refactor but pure cleanup. |
| 2026-06-19 | P2b ⏭️ deferred | `useContextMenuPosition` + `formatCount` util extraction; dedupe `getElementById('app-main-scroll')`. Pure cleanup. |
| 2026-06-19 | P2c ⏭️ deferred | Remove 4 duplicate `.toast-*` CSS blocks. Verify no longer-referenced selectors first. |
| 2026-06-19 | P2d ✅ | `Profile`, `ScheduledTasks`, `ImportSubscriptionDialog` — untracked `setTimeout` now stored + cleared in `onUnmounted` |
| 2026-06-19 | P2e ⏭️ deferred | Untyped params in `ScheduledTasks`/`SiteRuntimeManager`/`LogViewer`/`ImportSubscriptionDialog` — those files are `<script setup>` without `lang="ts"`; typing them properly means migrating to TS first. |
| 2026-06-19 | P2f ✅ (partial) | `RssSources.vue:249` `v-html="stripHtmlTags(...)"` → `{{ stripHtmlTags(...) }}` (was rendering plain text). `MusicProfileView` `AppEmptyState` — raw error string moved from `title` to `:copy`, title now "加载失败". `SettingsMenu` inline-style cleanup deferred (player-specific, 20+ sites). |

### Verification (2026-06-19)

- `npm run typecheck` (`vue-tsc --noEmit`): **pass** (clean).
- `npm run lint`: 41 errors, **all pre-existing** in files not touched here (confirmed via `git stash` baseline — same 41 errors). No new lint issues introduced.
