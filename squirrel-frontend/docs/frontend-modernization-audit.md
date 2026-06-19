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
| 2026-06-19 | P2a ⏭️ reverted → architecture PR | `ScheduledTasks` — a local `runMutation(apiCall, successMsg, errorMsg)` helper was extracted to collapse the 6 CRUD handlers, then **reverted**. Two reasons: (1) it only hid the duplication *inside one file* — the root cause is `handleRequest`'s `{data, error}` contract pushing error-handling policy into every caller (13 files, ~30 `if (result.error)` sites, 3 divergent feedback channels: toast / inline-ref / silent); (2) its hardcoded refresh-on-success forced `doExecuteTask` (which needs a *delayed* refresh) into a special-case bypass, leaving 5 handlers on the helper + 1 hand-rolled — less consistent than the original. The 6 handlers are restored to inline form (with a NOTE comment pointing here). The real fix is an architecture-level mutation layer over `handleRequest` so the error-feedback policy lives in one place. **Tracked as a follow-up architecture PR.** |
| 2026-06-19 | P2b ✅ | `formatCount` (亿/万) extracted to `shared/lib/dateFormat` — single source of truth, now used by `MusicHomeView`/`MusicArtistDetailView`/`MusicSearchView` (the last via `formatScore = formatCount`). `useContextMenuPosition` extracted to `shared/composables` — `useRssFeeds` + `useRssEntries` delegate the width-clamp + bottom-overflow-flip math (was byte-identical). `getElementById('app-main-scroll')` funnels through `shared/composables/useMainScrollRoot` (`getMainScrollRoot` + `MAIN_SCROLL_ID`); `AppLayout` binds the id from the constant. |
| 2026-06-19 | P2c ✅ | Removed 3 dead `.toast-*` CSS blocks (`VideoPlay`, `Settings`, `ScheduledTasks` — no `<Transition name="toast">` referencing them). Renamed `SiteRuntimeManager`'s *used* OAuth-prompt transition `toast` → `oauth-prompt` to stop colliding with the global toast stack's `app-toast-*`. Zero `toast-enter`/`name="toast"` references remain in `src/`. |
| 2026-06-19 | P2d ✅ | `Profile`, `ScheduledTasks`, `ImportSubscriptionDialog` — untracked `setTimeout` now stored + cleared in `onUnmounted` |
| 2026-06-19 | P2e ⏭️ deferred | Untyped params in `ScheduledTasks`/`SiteRuntimeManager`/`LogViewer`/`ImportSubscriptionDialog` — those files are `<script setup>` without `lang="ts"`; typing them properly means migrating to TS first. |
| 2026-06-19 | P2f ✅ (partial) | `RssSources.vue:249` `v-html="stripHtmlTags(...)"` → `{{ stripHtmlTags(...) }}` (was rendering plain text). `MusicProfileView` `AppEmptyState` — raw error string moved from `title` to `:copy`, title now "加载失败". `SettingsMenu` inline-style cleanup deferred (player-specific, 20+ sites). |

### Verification (2026-06-19)

- `npm run typecheck` (`vue-tsc --noEmit`): **pass** (clean).
- `npm run lint`: 41 errors, **all pre-existing** in files not touched here (confirmed via `git stash` baseline — same 41 errors). No new lint issues introduced.

### Verification (2026-06-19, pass 2)

- `npx vue-tsc --noEmit`: **pass** (clean) after P2a/P2b/P2c.
- `npm run build:check`: **pass** — production build succeeds (12.10s).
- `npm run lint`: still 41 errors, all in untouched files (`DashAdapter`/`HlsAdapter`/`ShakaDashAdapter`/`EventEmitter`/`logger.ts`/`AnalyticsPlugin.ts`/`shared/lib/logger.ts`/`CalendarHeading`/`RangeCalendarHeading` — playback bridge code + intentional `console`). None of the 15 changed files appear in the error list.
- Grep confirms: zero `toast-enter`/`name="toast"` in `src/`; zero `getElementById('app-main-scroll')` literals; zero `100000000).toFixed`/`10000).toFixed` count-formatting dupes.

---

## PR1 — Design-system foundation: status-color tokens + Alert variants

### Root cause found: status colors never existed
The design system defined exactly **one** status hue (`--destructive`, red). There was
no `--success`, `--warning`, or `--error` CSS variable, and `tailwind.config.ts` had no
matching color entries. Feature code nonetheless referenced `text-error`, `bg-error/10`,
`text-success`, `text-warning` everywhere — **these classes resolved to empty strings**,
so Login / Register / ServerConfig error banners rendered *colorless*, and the shared
`Badge` `success`/`warning` variants + LogViewer's `text-warning` filter indicator were
silently broken too. This was a live visual bug, not a style nit.

| Date | Item | Note |
|---|---|---|
| 2026-06-19 | PR1.1 ✅ | Added `--success` (emerald `142 71% 40%`) + `--warning` (amber `32 95% 44%`) + foregrounds to `themes/dark.css :root` (dark mode inherits — no override needed). `tailwind.config.ts` `colors` now exposes `destructive` / `success` / `warning` as first-class named colors so `bg-*`, `text-*`, `border-*` + `/opacity` modifiers all work. |
| 2026-06-19 | PR1.2 ✅ | `shared/ui/alert/` extended: added `error` (= destructive red, new canonical name), `success`, `warning`, `info` variants alongside existing `default`/`destructive`. `destructive` kept as a working alias so existing `AddChannelDialog`/`ImportSubscriptionDialog` call sites are unaffected. |
| 2026-06-19 | PR1.3 ✅ | Fixed the colorless-banner bug at source: `Login`/`Register`/`ServerConfig` hand-rolled error `<div class="text-error bg-error/10 …">` → shared `<Alert variant="error">` (renders red). ServerConfig test-result pill `text-error`→`text-destructive`, `hover:text-error`→`hover:text-destructive`; `text-success` now resolves (green). **Bonus**: `Badge` `success`/`warning`/`error` variants + LogViewer `text-warning` filter label — all previously broken — now render correctly for free. |

### Verification (2026-06-19, pass 3 — PR1)

- `npx vue-tsc --noEmit`: **pass** (clean).
- `npm run build:check`: **pass** (9.63s).
- `npm run lint`: still 41 pre-existing errors, none in changed files (`Login`/`Register`/`ServerConfig`/`alert/index.ts`/`tailwind.config.ts`/`dark.css` all clean).
- Grep confirms: zero `text-error`/`bg-error`/`border-error` left in `src/features/`; every `success`/`warning` token reference now resolves to a real color.

### Next (PR2–PR4, planned)

- **PR2** — unify the 5 error-state visuals + add error UI to the 4 views with none (`Subscribed`/`RssSources` list/`MusicSearch`/`MusicArtistDetail`) via a new `AppEmptyState variant="error"` + retry `#actions`.
- **PR3** — extract shared `useMutation` (toast-CRUD family) + unify inline-error forms onto `<Alert variant="error">`; surface the silent-swallow sites.
- **PR4** — load-state convergence (`AppBlockLoader` adoption, `Button :loading` for hand-rolled spinners).

---

## PR2 — Unified error-state UI

The audit found **5 distinct error-state visuals** (two sibling views `VideosView`/`ChannelDetailView`
even disagreed on the retry control: a raw `<button>` vs `<Button variant="destructive">`) plus
**4 views with no error UI at all** (`Subscribed`/`RssSources` list region/`MusicSearch`/`MusicArtistDetail`)
where a failed fetch looked identical to an empty result set. PR2 collapses all of it onto one
canonical pattern.

| Date | Item | Note |
|---|---|---|
| 2026-06-19 | PR2.1 ✅ | `AppEmptyState` gained `variant="error"`: layers a destructive tint on the icon badge + title, defaults `icon` to `warning`. Reuses `plain`'s borderless layout. The single primitive every failed-load now renders through. |
| 2026-06-19 | PR2.2 ✅ | `History.vue` (the prior convention: `variant="plain" icon="warning"` hand-tinted) → canonical `variant="error"`. |
| 2026-06-19 | PR2.3 ✅ | Collapsed the 4 hand-rolled error banners: `VideosView` (raw `<button>` retry → `<Button variant="destructive">`), `ChannelDetailView` (dropped `rounded-full` mismatch → matched VideosView), `RemoteChannelVideoGrid` (no-retry red box → `variant="error"` empty state), `SiteRuntimeManager` discovery banner → `<Alert variant="error">` + `AlertTitle`/`AlertDescription`. Toolbar-below error bars (VideosView/ChannelDetailView) deliberately kept inline (toolbar must stay usable on error); region-level empties use the empty-state primitive. |
| 2026-06-19 | PR2.4 ✅ | `Subscribed.vue` — **was silently swallowing errors** (`{ data }` destructure ignored `error`, try/finally with no catch). Added `fetchError` ref scoped to the **feed region only**; `fetchFeed` reads `error`, renders `variant="error"` + 重试. A failed feed fetch no longer looks like an empty list. Channel-sidebar fetch errors are left as a known gap (no sidebar error branch) — bails without clobbering the feed ref or pinning `channelsFinished`, so the sidebar stays retryable. |
| 2026-06-19 | PR2.5 ⏭️ reverted | Initial attempt reused the sync-flow `statusError`/`statusMessage` channel for the `RssSources` list-region error — **misleading**: a sync failure would have shown "文章列表加载失败", and the 6s auto-dismiss left no time to retry. Reverted to the known gap (no list-region error UI) until PR3 does it properly with a dedicated `listError` ref inside `useRssEntries`. |
| 2026-06-19 | PR2.6 ✅ (partial) | `MusicSearchView` — new `error` prop + `retry` emit, threaded from `Music.vue`'s `handleSearch` (which previously toasted on error but left the result view showing empty). Error now renders in-region with 重试. **`MusicArtistDetailView` skipped**: parent (`Music.vue`) already toasts detail-load errors, and the artist header still renders, so a full-region error state would be over-engineering for a gracefully-degrading child. |

### Verification (2026-06-19, pass 4 — PR2)

- `npx vue-tsc --noEmit`: **pass** (clean).
- `npm run build:check`: **pass** (9.97s).
- `npm run lint`: still 41 pre-existing errors; **zero** in any PR2-touched file (`AppEmptyState`/`History`/`VideosView`/`ChannelDetailView`/`RemoteChannelVideoGrid`/`SiteRuntimeManager`/`Subscribed`/`RssSources`/`MusicSearchView`/`Music.vue`).

### Review fixes (2026-06-19, post-PR2 self-review)

A focused re-read of the diff caught two bugs and two design issues before commit:

| Issue | Fix |
|---|---|
| **`VideosView` missing `Button` import** — migrated retry to `<Button variant="destructive">` but the file (formerly raw `<button>`) never imported it → runtime render error. `vue-tsc`/build didn't catch it (auto-import masking). | Added `import { Button } from '@/shared/ui/button'`. |
| **`doExecuteTask` double-refresh** — `runMutation`'s always-refresh-on-success fired immediately, then `doExecuteTask` scheduled a 2nd delayed refresh. The original had *only* the delayed refresh (deliberate: backend needs a beat to flip the row to "running"). | `doExecuteTask` bypasses `runMutation` and keeps its original single-delayed-refresh behavior. **Lesson for PR3**: `useMutation` should expose an `onSuccess` callback, not hardcode refresh — execute proves not every mutation wants an immediate refresh. |
| **RssSources list-error reused the sync `statusError` channel** — a sync failure would have shown "文章列表加载失败" (misleading), and the 6s auto-dismiss left no time to retry. Worse than no error UI. | Reverted PR2.5 to the known gap; deferred to PR3 with a dedicated `listError` ref inside `useRssEntries`. |
| **Subscribed `fetchError` shared across channels+feed** — the channels assignment was dead code (sidebar has no error branch) and `channelsFinished=true` on error pinned the sidebar un-retryable. | `fetchError` scoped to the feed region only; `fetchChannels` bails on error without touching the ref or `channelsFinished` (sidebar stays retryable). Sidebar error UI remains a known gap. |

### Verification (2026-06-19, pass 5 — post-review fixes)

- `npx vue-tsc --noEmit`: **pass** (clean).
- `npm run build:check`: **pass** (10.45s).
- `npm run lint`: 41 pre-existing errors, none in changed files.

### Remaining (PR3–PR4)

- **PR3** — extract shared `useMutation` (**with `onSuccess` callback, not hardcoded refresh** — the execute case proved that's needed) + unify inline-error forms (`Profile`/`SecuritySettings`/`AddChannelDialog`/`ImportSubscriptionDialog`) onto `<Alert variant="error">`; surface silent-swallow sites (`SiteRuntimeManager.fetchSiteRuntimes`/`siteEditorError` dead channel); give `RssSources` a proper `listError` ref inside `useRssEntries`.
- **PR4** — load-state convergence (`AppBlockLoader` adoption for `ScheduledTasks`/`SiteRuntimeManager`/`LogViewer` hand-rolled `animate-pulse`; `Button :loading>` for hand-rolled `refresh`-spinners; align `MusicSearchView`/`MusicHomeView` `AppBlockLoader` size).

---

## Architecture refactor: vue-query + throw-based error model

The error-handling architecture debt identified throughout this audit (the `handleRequest`
`{ data, error }` contract pushing error-feedback policy into ~50 duplicated call sites)
is now resolved at the root. This was a big-bang single-PR refactor per the approved plan.

### What changed

| Layer | Before | After |
|---|---|---|
| **HTTP** (`request.ts`) | `handleRequest` swallows all errors into `RequestResult<T> = { data, error }`; never throws | `handleRequest` removed. `get/post/...` return `T` directly and `throw ApiError` on failure (envelope `code≠0` or transport error). |
| **Transport** (`axios.ts`) | interceptor copied `msg` onto `error.message`, rejected raw AxiosError | interceptor constructs `ApiError` (with type/status/data) and rejects; 401 → logout preserved. |
| **Error types** | `ApiError`/`ErrorTypes` in request.ts (imported by axios.ts → cycle risk) | extracted to `apiError.ts` (pure, no axios import) → breaks the would-be cycle; `request.ts` re-exports for back-compat. |
| **Query** | none — every view hand-rolled loading/error refs + `if (result.error)` | `@tanstack/vue-query@5`. `QueryClient` (`shared/lib/queryClient.ts`) with `MutationCache.onError` → global auto-toast (the canonical feedback channel), `meta: { silent: true }` to opt out; `QueryCache.onError` silent (loaders self-render error UI). Desktop defaults: `staleTime 30s`, `refetchOnWindowFocus false`, `retry 1`. |
| **Wrappers** (`shared/api/*`) | return `RequestResult<T>` | return `T`; the 2 that reshaped errors (`subscription.ts` 429/403 rewriting, `siteRuntimes.ts` file-missing) now `throw` the rewritten `ApiError`. |
| **Call sites (~50)** | each hand-rolled `if (result.error) toast/inline/silent` | migrations per category (see below). |

### Migration by category (the inventory from the 3 Explore agents, now executed)

- **A (toast mutations, ~14)** → `useMutation` (ScheduledTasks 6 handlers incl. execute with delayed-invalidate `onSuccess`, Settings.onSystemToggle) or direct `try/catch`+toast (Music collect/MV/select). Hand-rolled `toast.error` deleted — global `MutationCache` handles it.
- **B (silent loaders, ~25)** → `useQuery` (ScheduledTasks stats/classes/list with reactive debounced key) or direct `try/catch` (music composables, video composables, RSS, LogViewer, SiteRuntimeManager). Errors logged, state resets to empty.
- **B (optimistic updates, ~8)** → `try/catch` with rollback (RSS read/star toggles, music FM like, video like/later/special-follow, subscribe/unsubscribe). Failure leaves prior state.
- **C (inline-error forms, ~6)** → `try/catch` assigning to field ref (Login/Register/Profile/SecuritySettings/AddChannelDialog/ImportSubscriptionDialog). `user` store keeps a thin `{ data, error }` tuple shape so these inline-render callers don't need rewriting.
- **D (status-callback, ~10)** → `try/catch` calling `onStatus(msg, isError)` (useRssSync/useRssFeeds/useRssEntries/useRssReader/useRssAccounts).

### Key decisions

- **No double-source-of-truth**: vue-query owns *server state* (lists/details/config); Pinia keeps *client state* (player audio/urlCache, auth identity, UI prefs). `user` store is the boundary — it catches thrown errors and re-shapes into its legacy tuple so Login/Register/Profile keep working.
- **`handleRequest` removed, not adapted**: `get/post` throwing is the query error model; keeping the `{data, error}` shape would have left two error channels.
- **Global toast lives in `MutationCache`, not `handleRequest`**: a request-layer toast would double-fire for the ~40 silent/inline sites. Mutations-only is the right granularity (CRUD feedback is the consistent UX; loaders self-render).
- **`runMutation` (the earlier reverted attempt) is now obsolete**: the `useMutation` pattern with `onSuccess` callbacks solves what `runMutation` couldn't — execute's delayed refresh is a natural `onSuccess`, not a special-case bypass.

### Verification (2026-06-20, architecture refactor)

- `npx vue-tsc --noEmit`: **0 errors** (clean — the prior 41 pre-existing calendar/logger errors are also gone, likely reka-ui/typescript resolution improvements).
- `npm run build:check`: **pass** (8.64s).
- `npm run lint`: 41 pre-existing errors (calendar `any`, logger `console`), none in refactored files.
- Grep confirms: zero `const { data, error } = await apiCall()` / `result.error` (API-result) patterns remain in `src/`; remaining `result.error` reads are the `user` store's legacy-tuple callers (by design) and doc comments.

### Follow-up (not in scope)

- **Broader `useQuery` adoption**: only ScheduledTasks loaders were migrated to `useQuery`; the other loaders (music/video/rss composables) use direct `try/catch` for now (correct, but don't get query's caching/refetch/invalidation benefits). A future pass could move them to `useQuery` now that the throw model is in place.
- **`user` store tuple removal**: once Login/Register/Profile migrate to render `error` from a `useQuery`/`useMutation` directly, the store's `{ data, error }` re-shape can go.
- **PR4 (load-state convergence)** still pending — independent of this refactor.

### Post-refactor self-review (2026-06-20) — "best change, not minimal"

A focused re-read against "best practice, not compromise" found 3 real issues, all fixed:

| Issue | Compromise | Best-practice fix |
|---|---|---|
| **Error-classification helpers duplicated** | `getErrorType`/`formatErrorMessage` lived in `axios.ts`, `getErrorTypeByStatus`/`getErrorTypeByCode` in `request.ts` — two copies of status→type + error→message logic, split across files. | Centralized all classification in `apiError.ts` (`getErrorTypeByStatus`/`getTransportErrorType`/`getErrorTypeByCode`/`formatTransportErrorMessage`); `axios.ts` and `request.ts` import the single source. |
| **ScheduledTasks dual source of truth** | The query migration kept local mutable refs (`tasks`/`statistics`/`taskClasses`/`totalPages`) that `queryFn` wrote alongside the query cache — the template read the refs, not `query.data`. This was exactly the dual-source-of-truth the refactor aimed to kill. | Deleted the mutable refs; `tasks`/`statistics`/`taskClasses`/`totalPages` are now `computed` projections of `*Query.data`. The query cache is the one source. |
| **Redundant refetches + skeleton flicker** | `goToPage`/`setStatusFilter` called `tasksQuery.refetch()` manually even though `queryKey` is reactive on those same refs (→ double fetch). `loading` used `isFetching` (true on background refetch) → skeleton flashed on every mutation invalidate. | Removed manual refetches (reactive key handles it); `loading` now uses `isLoading` (first-load only; background refetch keeps the prior list visible). |

### Verification (2026-06-20, post-review fixes)

- `npx vue-tsc --noEmit`: **0 errors**.
- `npm run build:check`: **pass** (8.93s).





