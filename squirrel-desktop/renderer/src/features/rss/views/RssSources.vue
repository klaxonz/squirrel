<template>
  <AppPageShell variant="compact" surface="organize" width="fluid" fill>
    <!--
      The RSS three-pane owns the window (global app rail
      collapses via route meta). Source column is a quiet tree + one sync menu.
    -->
    <AppTwoColumnLayout
      sidebar-always
      preset="rss"
      :sidebar-collapsed="sourcePaneCollapsed"
      :main-scroll="false"
      class="rss-workspace"
    >
      <template #sidebar>
        <AppSidebarHeader
          title="订阅库"
        >
          <template #actions>
            <Button
              text severity="secondary"
              size="sm" icon-only
              class="rss-source-pane-toggle"
              title="收起订阅库"
              aria-label="收起订阅库"
              @click="sourcePaneCollapsed = true"
            >
              <AppIcon name="panelClose" class="h-4 w-4" />
            </Button>
            <Button
              severity="secondary" outlined
              size="sm" icon-only
              class="rss-add-account-button"
              aria-label="添加账号"
              @click="openAddAccount"
            >
              <AppIcon name="plus" class="h-4 w-4" />
            </Button>
          </template>
        </AppSidebarHeader>

        <div class="app-pane__controls app-pane__controls--compact rss-source-controls">
          <div ref="accountDropdownRef">
            <AccountDropdown
              :accounts="accounts"
              :selected-id="selectedAccountId"
              :selected-name="selectedAccount?.name || ''"
              :selected-provider="selectedAccount?.provider || ''"
              :open="showAccountDropdown"
              @toggle="showAccountDropdown = !showAccountDropdown"
              @select="(id) => { selectAccount(id); showAccountDropdown = false }"
              @edit="(acc) => { openEditAccount(acc); showAccountDropdown = false }"
              @delete="(acc) => { confirmDeleteAccount(acc); showAccountDropdown = false }"
            />
          </div>

          <div
            v-if="selectedAccount"
            class="rss-sync-status"
            :class="{
              'is-active': syncing,
              'is-error': statusError || (!statusMessage && !!selectedAccount.last_error),
            }"
          >
            <span class="rss-sync-status__indicator" aria-hidden="true" />
            <span class="rss-sync-status__copy" :title="statusMessage">
              {{ statusMessage || selectedAccount.last_error || (selectedAccount.last_sync_at ? '上次同步 ' + formatDate(selectedAccount.last_sync_at) : '尚未同步') }}
            </span>
            <div class="rss-sync-status__menu" role="group" aria-label="同步">
              <Button
                text severity="secondary"
                size="sm" icon-only
                class="rss-sync-status__menu-btn"
                :disabled="syncing"
                title="轻量同步"
                aria-label="轻量同步"
                @click="syncSelectedAccount(false)"
              >
                <AppIcon name="refresh" class="h-3.5 w-3.5" />
              </Button>
              <Button
                text severity="secondary"
                size="sm" icon-only
                class="rss-sync-status__menu-btn"
                :disabled="syncing"
                title="全量同步"
                aria-label="全量同步"
                @click="syncSelectedAccount(true)"
              >
                <AppIcon name="download" class="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <AppSearchInput
            v-model="feedSearch"
            placeholder="搜索订阅源"
            aria-label="搜索订阅源"
          />
        </div>

        <FeedFolderTree
          :folders="feedFolders"
          :expanded-folders="collapsedFolders"
          :selected-feed-id="selectedFeedId"
          :total-feeds="filteredFeeds.length"
          :has-account="!!selectedAccount"
          :can-manage-subscriptions="canManageSubscriptions"
          :loading="loadingFeeds"
          :error="accountsError || feedsError"
          @select-all="selectedFeedId = null; loadEntries(true)"
          @add-feed="showSubscribeModal = true"
          @toggle-folder="toggleFolder"
          @select-feed="selectFeedAndShowAll"
          @feed-context-menu="showFeedContextMenu"
          @unsubscribe-feed="requestUnsubscribeFeed"
          @retry="loadAll"
        />
      </template>

      <!-- Middle: article list -->
      <section class="app-pane app-pane--list rss-entry-pane">
        <header class="app-pane__header rss-entry-header">
          <div class="app-pane__header-row">
            <div class="rss-entry-header__identity">
              <Button
                v-if="sourcePaneCollapsed"
                text severity="secondary"
                size="sm" icon-only
                class="rss-source-pane-toggle"
                title="展开订阅库"
                aria-label="展开订阅库"
                @click="sourcePaneCollapsed = false"
              >
                <AppIcon name="panelOpen" class="h-4 w-4" />
              </Button>

              <div class="app-pane__header-copy">
                <div
                  v-if="hasFeedNavStack || selectedFeedTitle"
                  class="app-pane__header-title-row"
                >
                  <Button
                    v-if="hasFeedNavStack"
                    text severity="secondary"
                    size="sm" icon-only
                    class="rss-back-button"
                    title="返回之前的列表"
                    aria-label="返回之前的列表"
                    @click="handleFeedBack"
                  >
                    <AppIcon name="back" class="h-3 w-3" />
                  </Button>
                  <h2 v-if="selectedFeedTitle" class="app-h4 truncate">
                    {{ selectedFeedTitle }}
                  </h2>
                </div>
                <div class="app-pane__header-subtitle">
                  <span>{{ selectedFeedSubtitle }}</span>
                </div>
              </div>
            </div>

            <div class="app-pane__header-actions">
              <Button
                text severity="secondary"
                size="sm" icon-only
                :disabled="loading"
                title="刷新文章"
                aria-label="刷新文章"
                @click="loadAll"
              >
                <AppSpinner v-if="loading" size="sm" />
                <AppIcon v-else name="refresh" class="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div class="rss-entry-tools">
            <AppSegmentedControl
              v-model="activeFilter"
              :options="rssFilterOptions"
              aria-label="文章筛选"
              size="sm"
              class="rss-filter-tabs"
            >
              <template #option="{ option }">
                <AppIcon v-if="option.icon" :name="option.icon" class="h-3 w-3" />
                <span>{{ option.label }}</span>
              </template>
            </AppSegmentedControl>
          </div>
        </header>

        <div ref="entriesContainer" class="app-pane__list custom-scrollbar rss-entry-list">
          <div class="rss-entry-list__inner">

            <div
              v-if="loadingEntries"
              class="rss-entry-skeleton-list"
              aria-label="正在加载文章"
              aria-busy="true"
            >
              <RssEntrySkeleton v-for="index in 6" :key="index" />
            </div>

            <!-- Empty view -->
            <div v-else-if="entriesError" class="app-page-empty app-page-empty--compact">
              <AppEmptyState
                variant="error"
                title="文章加载失败"
                :copy="entriesError"
              >
                <template #actions>
                  <Button severity="secondary" outlined size="sm" @click="loadEntries(true)">重试</Button>
                </template>
              </AppEmptyState>
            </div>

            <div v-else-if="filteredEntries.length === 0" class="app-page-empty app-page-empty--compact">
              <AppEmptyState
                variant="plain"
                icon="inbox"
                :title="activeFilter === 'recent' ? '暂无浏览记录' : '暂无相关文章'"
                :copy="activeFilter === 'recent' ? '浏览文章后，这里会记录您最近看过的内容。' : (selectedAccount ? '当前无对应文章，可点击同步获取最新内容。' : '请先添加并选择您的 RSS 账号。')"
              />
            </div>

            <!-- Articles List -->
            <div v-else class="rss-entry-stack">
              <AppSelectableListItem
                v-for="entry in filteredEntries"
                :key="entry.id"
                :data-entry-id="String(entry.id)"
                class="rss-entry-item group"
                :class="{ 'is-read': entry.is_read }"
                variant="flush"
                :selected="readingEntry !== null && String(readingEntry.id) === String(entry.id)"
                :aria-label="entry.is_read ? `已读：${entry.title}` : `未读：${entry.title}`"
                @click="openReader(entry)"
                @keydown.enter.self.prevent="openReader(entry)"
                @keydown.space.self.prevent="openReader(entry)"
                @contextmenu.prevent.stop="showArticleContextMenu(entry, $event)"
              >
                <div class="rss-entry-item__meta-row">
                  <Button
                    text severity="secondary"
                    size="sm"
                    type="button"
                    class="rss-entry-item__source"
                    title="查看该订阅源"
                    @click.stop="pushFeedNavStack(); selectFeedAndShowAll(entry.feed_id)"
                  >
                    <SiteIcon
                      :icon-url="getFeedIconUrl(entry.feed_id)"
                      size="xs"
                      rounded="sm"
                      class="shrink-0"
                    />
                    <span>{{ getFeedTitle(entry.feed_id) }}</span>
                  </Button>
                  <div class="rss-entry-item__status">
                    <AppIcon v-if="entry.is_starred" name="star" class="h-3 w-3 text-warning fill-warning" />
                    <span class="rss-entry-item__date">{{ activeFilter === 'recent' ? formatRelativeTime((entry as RecentEntry).viewed_at) : formatDate(entry.published_at) }}</span>
                  </div>
                </div>

                <div class="rss-entry-item__content">
                  <h4
                    class="rss-entry-item__title"
                  >
                    {{ entry.title }}
                  </h4>
                  <p
                    v-if="entry.excerpt || entry.summary"
                    class="rss-entry-item__summary"
                  >{{ entryPreviewText(entry) }}</p>
                </div>

                <div
                  v-if="entry.author || getFeedCategory(entry.feed_id)"
                  class="rss-entry-item__footer"
                >
                  <span v-if="entry.author" class="truncate">{{ entry.author }}</span>
                  <span v-if="entry.author && getFeedCategory(entry.feed_id)" aria-hidden="true">·</span>
                  <span v-if="getFeedCategory(entry.feed_id)" class="truncate">
                    {{ getFeedCategory(entry.feed_id) }}
                  </span>
                </div>
              </AppSelectableListItem>
            </div>

            <!-- Infinite Scroll Loader Anchor -->
            <div ref="loadMoreTrigger" class="rss-entry-load-more">
              <div
                v-if="!loadingEntries && filteredEntries.length > 0 && loadingMoreEntries"
                class="rss-entry-load-more__status"
              >
                <AppBounceDots />
                <span>加载更多</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Right Column: Permanent Article Content Reader -->
      <main class="app-pane app-pane--fluid rss-reader-pane">
        <!-- If an article is selected, render it -->
        <div v-if="readingEntry" class="rss-reader-active">
          <!-- Reader Header (Clean compact toolbar) -->
          <header class="app-pane__header rss-reader-toolbar">
            <div class="app-pane__header-row rss-reader-toolbar__row">
              <div class="rss-reader-toolbar__identity">
                <Button
                  text severity="secondary"
                  size="sm"
                  @click="pushFeedNavStack(); selectFeedAndShowAll(readingEntry.feed_id)"
                  class="rss-reader-source-button"
                  title="查看该订阅源的所有文章"
                >
                  <SiteIcon :icon-url="getFeedIconUrl(readingEntry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
                  <span class="rss-reader-source-title" :title="getFeedTitle(readingEntry.feed_id)">
                    {{ getFeedTitle(readingEntry.feed_id) }}
                  </span>
                </Button>
                <span class="rss-reader-toolbar__domain">
                  {{ getDisplayDomain(readingEntry.canonical_url) }}
                </span>
              </div>

              <div class="app-pane__header-actions rss-reader-actions">
              <!-- 应用内预览原文 -->
              <Button
                text severity="secondary"
                size="sm" icon-only
                title="在应用内打开原文"
                aria-label="在应用内打开原文"
                @click="openInAppBrowser"
              >
                <AppIcon name="siteFallback" class="h-4 w-4" />
              </Button>

              <!-- 在系统浏览器打开 -->
              <Button
                title="在系统浏览器打开"
                aria-label="在系统浏览器打开"
                text
                severity="secondary"
                size="sm"
                icon-only
                @click="openExternalUrl(readingEntry.canonical_url)"
              >
                <AppIcon name="externalLink" class="h-4 w-4" />
              </Button>

              <!-- 收藏 / 取消收藏 -->
              <Button
                text severity="secondary"
                size="sm" icon-only
                :class="readingEntry.is_starred ? 'text-warning' : ''"
                :title="readingEntry.is_starred ? '取消收藏' : '收藏文章'"
                :aria-label="readingEntry.is_starred ? '取消收藏' : '收藏文章'"
                :aria-pressed="readingEntry.is_starred"
                @click="toggleStarStatus(readingEntry)"
              >
                <AppIcon name="star" class="h-4 w-4" :class="readingEntry.is_starred ? 'text-warning fill-amber-500' : ''" />
              </Button>

              <!-- 取消订阅该源 -->
              <Button
                v-if="canManageSubscriptions"
                text severity="secondary"
                size="sm" icon-only
                class="hover:bg-destructive/10 hover:text-destructive"
                title="取消订阅该源"
                aria-label="取消订阅该源"
                @click="requestUnsubscribeByEntry(readingEntry)"
              >
                <AppIcon name="trash" class="h-4 w-4" />
              </Button>

              <!-- Reader Settings -->
              <div class="relative" ref="readerSettingsRef">
                <Button
                  text severity="secondary"
                  size="sm" icon-only
                  :aria-expanded="showReaderSettings"
                  title="阅读个性化设置"
                  aria-label="阅读个性化设置"
                  @click="showReaderSettings = !showReaderSettings"
                >
                  <AppIcon name="settingsPanel" class="h-4 w-4" />
                </Button>

                <ReaderSettingsPanel
                  :visible="showReaderSettings"
                  :font-family="readerFontFamily"
                  :font-size="readerFontSize"
                  @update:visible="showReaderSettings = $event"
                  @update:font-family="readerFontFamily = $event; saveReaderPrefs()"
                  @update:font-size="setReaderFontSize"
                  @save="saveReaderPrefs()"
                />
              </div>
              </div>
            </div>
          </header>

          <!-- Reader Body Scroll Container -->
          <div
            ref="readerScrollContainer"
            class="app-scroll-pane custom-scrollbar rss-reader-body"
          >
            <article class="rss-reader-article app-reader-width">
              <header class="rss-reader-article__header">
                <span class="rss-reader-article__category">
                  {{ getFeedCategory(readingEntry.feed_id) || '未分类' }}
                </span>
                <h1
                  @click="openInAppBrowser"
                  class="rss-reader-title"
                  title="点击在应用内打开原文"
                >
                  {{ readingEntry.title }}
                </h1>
                <div class="rss-reader-meta">
                  <span v-if="readingEntry.author">{{ readingEntry.author }}</span>
                  <span v-if="readingEntry.author" aria-hidden="true">·</span>
                  <time>{{ formatDate(readingEntry.published_at) }}</time>
                </div>
              </header>

              <div
                v-if="loadingArticleContent"
                class="text-muted-foreground"
                :class="readerContentClass"
                :style="{ fontSize: readerFontSize + 'px' }"
              >
                正在加载正文…
              </div>
              <div
                v-else-if="sanitizedArticleHtml"
                :class="readerContentClass"
                :style="{ fontSize: readerFontSize + 'px' }"
                @click="handleContentClick"
                v-html="sanitizedArticleHtml"
              />
              <p
                v-else
                class="text-muted-foreground"
                :class="readerContentClass"
                :style="{ fontSize: readerFontSize + 'px' }"
              >
                该文章暂无正文内容。
              </p>
            </article>
          </div>
        </div>

        <!-- If no article is selected, render a neutral placeholder -->
        <div v-else class="rss-reader-empty">
          <AppEmptyState
            variant="plain"
            icon="library"
            title="选择文章开始阅读"
            copy="从文章列表选择一篇内容，正文会在这里保持专注地展开。"
          />
        </div>
      </main>
    </AppTwoColumnLayout>

    <!-- 3. Add / Edit RSS Account Dialog -->
    <AccountEditDialog
      v-model:open="showAddEditModal"
      v-model:form="accountForm"
      :providers="providers"
      :base-url-placeholder="baseUrlPlaceholder"
      :credential-placeholder="credentialPlaceholder"
      :form-message="formMessage"
      :form-error="formError"
      :requires-username="requiresUsername"
      :can-save-form="canSaveForm"
      :can-test-form="canTestForm"
      :saving="saving"
      :testing="testing"
      :max-sync-entry-limit="MAX_RSS_SYNC_ENTRY_LIMIT"
      @save="saveAccount"
      @test="testForm"
    />

    <!-- 4. Delete Account Confirmation Dialog -->
    <DeleteAccountDialog
      v-model:open="showDeleteConfirmModal"
      :account-name="accountToDelete?.name || ''"
      :deleting="deleting"
      @confirm="handleDeleteAccount"
    />

    <ConfirmDialog
      v-model:open="showUnsubscribeConfirm"
      icon="trash"
      icon-bg-class="bg-destructive/10"
      icon-class="text-destructive"
      title="确认取消订阅？"
      :description="feedToUnsubscribe ? `将从服务端取消「${feedToUnsubscribe.title}」，并删除本地同步的文章记录。` : ''"
      cancel-label="保留订阅"
      confirm-label="取消订阅"
      confirm-variant="destructive"
      :confirming="unsubscribingFeed"
      @confirm="confirmUnsubscribeFeed"
    />

    <Dialog :open="showSubscribeModal" @update:open="$event ? showSubscribeModal = true : closeSubscribeModal()">
      <DialogContent class="rss-subscribe-dialog app-dialog-surface !overflow-visible">
        <DialogHeader class="app-dialog-form-header">
          <DialogTitle class="app-dialog-form-title">添加订阅源</DialogTitle>
          <DialogDescription class="app-dialog-form-description">
            输入 RSS 订阅源 URL，将其添加到「{{ selectedAccount?.name }}」账号。
          </DialogDescription>
        </DialogHeader>

        <div class="app-dialog-form-body">
          <div class="app-dialog-form-field">
            <label class="app-dialog-form-label">订阅源 URL</label>
            <div class="app-icon-field">
              <AppIcon name="link" class="app-icon-field__icon" />
              <Input fluid
                v-model="subscribeForm.feedUrl"
                class="app-form-input app-form-input--with-icon"
                placeholder="https://example.com/rss/feed.xml"
              />
            </div>
          </div>

          <div class="app-dialog-form-field" ref="categoryDropdownRef">
            <label class="app-dialog-form-label">分类</label>
            <Button
              severity="secondary" outlined
              size="sm"
              @click="showCategoryDropdown = !showCategoryDropdown"
              class="rss-subscribe-dialog__category-button app-toolbar-control"
              :class="subscribeForm.category ? 'text-foreground' : 'text-muted-foreground/60'"
            >
              <div class="flex items-center gap-2 min-w-0">
                <AppIcon name="list" class="h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
                <span class="truncate">{{ subscribeForm.category || '未选择（自动带出）' }}</span>
              </div>
              <AppIcon
                name="chevronDown"
                class="h-3.5 w-3.5 shrink-0 text-muted-foreground/50 transition-transform"
                :class="{ 'rotate-180': showCategoryDropdown }"
              />
            </Button>

            <AppFloatingList
              v-if="showCategoryDropdown"
              class="rss-subscribe-dialog__category-menu"
              max-height="12.5rem"
            >
              <AppListOption
                :selected="!subscribeForm.category"
                @click="subscribeForm.category = ''; showCategoryDropdown = false"
              >
                <span>未分类</span>
              </AppListOption>
              <AppListOption
                v-for="cat in existingCategories"
                :key="cat"
                :selected="subscribeForm.category === cat"
                @click="subscribeForm.category = cat; showCategoryDropdown = false"
              >
                <span>{{ cat }}</span>
              </AppListOption>
              <AppListEmpty v-if="!existingCategories.length">暂无分类</AppListEmpty>
              <AppListSeparator />
              <div v-if="!showCustomCategoryInput" class="p-1">
                <Button
                  text severity="secondary"
                  size="sm"
                  @click="showCustomCategoryInput = true"
                  class="rss-subscribe-dialog__new-category"
                >
                  <AppIcon name="plus" class="h-3.5 w-3.5" />
                  新建分类
                </Button>
              </div>
              <div v-else class="p-2">
                <div class="relative">
                  <Input fluid
                    v-model="subscribeForm.customCategory"
                    class="app-form-input rss-subscribe-dialog__custom-input"
                    placeholder="输入分类名称"
                    @keyup.enter="confirmCustomCategory"
                    ref="customCategoryInputRef"
                  />
                  <Button
                    text severity="secondary"
                    size="sm" icon-only
                    @click="confirmCustomCategory"
                    class="rss-subscribe-dialog__confirm-category"
                  >
                    <AppIcon name="check" class="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </AppFloatingList>
          </div>

          <Transition name="fade">
            <div
              v-if="subscribeMessage"
              class="app-dialog-message"
              :class="subscribeError ? 'is-error' : 'is-success'"
            >
              <AppIcon
                :name="subscribeError ? 'error' : 'check'"
                class="app-dialog-message__icon"
              />
              <span>{{ subscribeMessage }}</span>
            </div>
          </Transition>
        </div>

        <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
          <Button
            type="button"
            severity="secondary" outlined
            size="sm"
            @click="closeSubscribeModal"
          >
            取消
          </Button>
          <Button
            type="button"
            size="sm"
            :disabled="!subscribeForm.feedUrl.trim()"
            :loading="subscribingFeed"
            @click="handleSubscribeFeed"
          >
            添加订阅
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>



    <!-- Beautiful Full-screen Image Lightbox -->
    <RssImageLightbox
      :src="activeLightboxImg"
      :scale="lightboxScale"
      @close="closeLightbox"
    />

    <!-- Customized Right-Click Context Menu -->
    <RssArticleContextMenu
      :visible="showContextMenu"
      :entry="contextMenuEntry"
      :feed="contextMenuFeedResolved"
      :position="contextMenuPosition"
      :can-manage-subscriptions="canManageSubscriptions"
      :ref="bindArticleMenuRef"
      @toggle-read="toggleReadStatus"
      @toggle-star="toggleStarStatus"
      @go-to-feed="goToFeedFromContextMenu"
      @set-open-method="(feed, method) => setFeedOpenMethod(feed, method)"
      @batch-read="(scope, read) => batchUpdateReadStatus(scope, read)"
      @unsubscribe="requestUnsubscribeByEntry"
      @copy-link="copyArticleLink"
      @open-external="openInExternalBrowser"
      @close="closeContextMenu"
    />

    <!-- Customized Feed Right-Click Context Menu -->
    <RssFeedContextMenu
      :visible="showFeedContextMenuState"
      :feed="contextMenuFeed"
      :position="feedContextMenuPosition"
      :can-manage-subscriptions="canManageSubscriptions"
      :ref="bindFeedMenuRef"
      @mark-all-read="markFeedAllAsRead"
      @sync-feed="syncFeedFromContextMenu"
      @copy-link="copyFeedLink"
      @open-site="openFeedSiteInExternalBrowser"
      @set-open-method="(feed, method) => setFeedOpenMethod(feed, method)"
      @unsubscribe="requestUnsubscribeFeed"
      @close="closeFeedContextMenu"
    />
  </AppPageShell>
</template>

<script setup lang="ts">
import { nextEntryIndex } from '@/features/rss/composables/rssEntryNav'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppBounceDots from '@/shared/components/AppBounceDots.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import ReaderSettingsPanel from '@/features/rss/components/ReaderSettingsPanel.vue'
import AccountDropdown from '@/features/rss/components/AccountDropdown.vue'
import FeedFolderTree from '@/features/rss/components/FeedFolderTree.vue'
import RssEntrySkeleton from '@/features/rss/components/RssEntrySkeleton.vue'
import AccountEditDialog from '@/features/rss/components/AccountEditDialog.vue'
import DeleteAccountDialog from '@/features/rss/components/DeleteAccountDialog.vue'
import RssImageLightbox from '@/features/rss/components/RssImageLightbox.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppSidebarHeader from '@/shared/components/layout/AppSidebarHeader.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListEmpty from '@/shared/components/layout/AppListEmpty.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import AppListSeparator from '@/shared/components/layout/AppListSeparator.vue'
import AppSelectableListItem from '@/shared/components/layout/AppSelectableListItem.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import { formatDate } from '@/shared/lib/dateFormat'
import { openExternalUrl } from '@/shared/lib/externalUrl'
import { MAX_RSS_SYNC_ENTRY_LIMIT, useRssAccounts } from '@/features/rss/composables/useRssAccounts'
import { useRssFeeds } from '@/features/rss/composables/useRssFeeds'
import { useRssEntries } from '@/features/rss/composables/useRssEntries'
import { useRssReader } from '@/features/rss/composables/useRssReader'
import { useRssSync } from '@/features/rss/composables/useRssSync'
import { useRssStatus } from '@/features/rss/composables/useRssStatus'
import { useRssFeedHeader } from '@/features/rss/composables/useRssFeedHeader'
import { useRssContextMenu } from '@/features/rss/composables/useRssContextMenu'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { useUIStore } from '@/shared/stores/ui'
import RssFeedContextMenu from '@/features/rss/components/RssFeedContextMenu.vue'
import RssArticleContextMenu from '@/features/rss/components/RssArticleContextMenu.vue'
import type { RssEntry, RssFeed, RecentEntry } from '@/features/rss/types/rss'
import type { AppIconName } from '@/shared/icons/app-icons'

// Cross-cutting UI state
const loading = ref(false)
const sourcePaneCollapsed = ref(false)
const uiStore = useUIStore()
const rssArticleSearch = computed(() => uiStore.getSearchQuery('rss'))
const rssArticleSearchTrigger = computed(() => uiStore.getSearchTrigger('rss'))
const rssFilterOptions: Array<{ value: string; label: string; icon: AppIconName }> = [
  { value: 'all', label: '全部', icon: 'list' },
  { value: 'unread', label: '未读', icon: 'inbox' },
  { value: 'starred', label: '星标', icon: 'star' },
  { value: 'recent', label: '最近', icon: 'history' },
]

// ponytail: status banner state + auto-dismiss timer live in useRssStatus so
// the "don't auto-dismiss progress messages" policy + timer cleanup are owned
// in one place rather than inlined beside six composable wiring blocks.
const { statusMessage, statusError, onStatus, dispose: disposeStatus } = useRssStatus()

// Forward ref for loadAll (defined after composables)
let loadAllImpl: () => Promise<void> = async () => {}

const getDisplayDomain = (urlStr?: string | null) => {
  if (!urlStr) return ''
  try {
    return new URL(urlStr).hostname
  } catch {
    return urlStr || ''
  }
}

// Initialize composables
const {
  providers,
  accounts,
  accountsError,
  selectedAccountId,
  showAddEditModal,
  showDeleteConfirmModal,
  accountToDelete,
  showAccountDropdown,
  saving,
  testing,
  deleting,
  accountForm,
  formMessage,
  formError,
  selectedAccount,
  baseUrlPlaceholder,
  credentialPlaceholder,
  requiresUsername,
  canSaveForm,
  canTestForm,
  openAddAccount,
  openEditAccount,
  confirmDeleteAccount,
  loadAccounts,
  saveAccount,
  testForm,
  handleDeleteAccount,
} = useRssAccounts({
  onRefresh: () => loadAllImpl(),
  onStatus,
})

const canManageSubscriptions = computed(() => {
  const account = selectedAccount.value
  if (!account) return false
  return account.capabilities?.manage_subscriptions ?? account.provider !== 'fever'
})

const {
  feeds,
  feedsError,
  selectedFeedId,
  loadingFeeds,
  showSubscribeModal,
  subscribingFeed,
  showCategoryDropdown,
  showCustomCategoryInput,
  customCategoryInputRef,
  categoryDropdownRef,
  subscribeForm,
  subscribeMessage,
  subscribeError,
  feedSearch,
  collapsedFolders,
  showFeedContextMenuState,
  feedContextMenuRef,
  feedContextMenuPosition,
  contextMenuFeed,
  filteredFeeds,
  existingCategories,
  feedFolders,
  loadFeeds,
  confirmCustomCategory,
  closeSubscribeModal,
  handleSubscribeFeed,
  toggleFolder,
  selectFeed,
  findFeedByEntry,
  getFeedTitle,
  getFeedCategory,
  getFeedIconUrl,
  handleUnsubscribeFeed,
  showFeedContextMenu,
  closeFeedContextMenu,
  setFeedOpenMethod,
  syncFeedFromContextMenu,
  markFeedAllAsRead,
  copyFeedLink,
  openFeedSiteInExternalBrowser,
} = useRssFeeds({
  selectedAccountId,
  canManageSubscriptions,
  onRefreshEntries: (isReset) => loadEntries(isReset ?? true),
  onStatus,
})

const {
  readingEntry,
  readerScrollContainer,
  readerFontSize,
  readerFontFamily,
  showReaderSettings,
  readerSettingsRef,
  activeLightboxImg,
  lightboxScale,

  readerFontClass,
  readerContentClass,
  sanitizedArticleHtml,
  loadingArticleContent,
  setReaderFontSize,
  saveReaderPrefs,
  handleContentClick,
  closeLightbox,
  handleKeyDown,
  openInAppBrowser,
  entryPreviewText,
  stripHtmlTags,
  formatRelativeTime,
} = useRssReader({
  onStatus,
})

const {
  activeFilter,
  loadingEntries,
  totalEntries,
  loadingMoreEntries,
  entriesError,
  recentlyViewed,
  entriesContainer,
  loadMoreTrigger,
  hasFeedNavStack,
  showContextMenu,
  contextMenuPosition,
  contextMenuEntry,
  contextMenuRef,
  filteredEntries,
  loadEntries,
  loadRecentlyViewed,
  recordRecentlyViewed,
  pushFeedNavStack,
  goBackFromFeed,
  clearFeedNavStack,
  toggleReadStatus,
  batchUpdateReadStatus,
  toggleStarStatus,
  showArticleContextMenu,
  closeContextMenu: entriesCloseContextMenu,
  copyArticleLink,
  openInExternalBrowser,
  goToFeedFromContextMenu,
  initObserver,
} = useRssEntries({
  selectedAccountId,
  selectedFeedId,
  feeds,
  searchQuery: rssArticleSearch,
  searchTrigger: rssArticleSearchTrigger,
  getFeedTitle,
  readingEntry,
  onStatus,
})

// 单一来源仍是 useNavigationHistory：RSS 内部的 "feed → feed" 二级栈
// 通过 registerInternalBackHandler 暴露给应用导航，让鼠标侧键、
// Alt+← 快捷键和页内"返回"按钮保持一致。
const appNavigation = useNavigationHistory()

const handleFeedBack = (): boolean => goBackFromFeed()

// Sync polling owns its request state and timer cleanup.
const {
  syncing,
  syncSelectedAccount,
  resumeSyncPollingIfRunning,
  stopSyncPolling,
} = useRssSync({
  selectedAccountId,
  onStatus,
  loadAccounts,
  loadFeeds,
  loadEntries,
})

// ponytail: header title/subtitle derivation lives in useRssFeedHeader so the
// "which filter context wins the header" formula is one import, not an inline
// block interleaved with orchestration.
const { selectedFeedTitle, selectedFeedSubtitle } = useRssFeedHeader({
  activeFilter,
  selectedFeedId,
  feeds,
  recentlyViewed,
  totalEntries,
  selectedAccount,
})

// ponytail: context-menu close + child-ref bridging + article-menu feed
// resolution live in useRssContextMenu. The two bind helpers were copy-pasted
// with identical `instance.rootRef` extraction; centralised behind one bridge.
const {
  closeContextMenu,
  bindFeedMenuRef,
  bindArticleMenuRef,
  contextMenuFeedResolved,
} = useRssContextMenu({
  feedContextMenuRef,
  contextMenuRef,
  closeFeedContextMenu,
  closeArticleContextMenu: entriesCloseContextMenu,
  contextMenuEntry,
  findFeedByEntry,
})

loadAllImpl = async () => {
  loading.value = true
  try {
    await loadAccounts()
    await Promise.all([
      loadFeeds(),
      loadEntries(true),
    ])
  } finally {
    loading.value = false
  }
}

const loadAll = loadAllImpl

const selectFeedAndShowAll = async (feedId: number) => {
  if (activeFilter.value === 'recent') {
    await selectFeed(feedId, false)
    activeFilter.value = 'all'
    return
  }
  await selectFeed(feedId)
}

const openReader = (entry: RssEntry) => {
  readingEntry.value = entry

  const feed = findFeedByEntry(entry.feed_id)
  const method = feed?.open_method

  if (method === 'external_browser') {
    void openExternalUrl(entry.canonical_url)
    if (!entry.is_read) {
      toggleReadStatus(entry, false)
    }
    recordRecentlyViewed(entry)
    return
  }

  if (!entry.is_read) {
    toggleReadStatus(entry, false)
  }
  recordRecentlyViewed(entry)

  if (method === 'app_browser') {
    void openInAppBrowser()
  }
}


const isTypingTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return target.isContentEditable
    || tag === 'INPUT'
    || tag === 'TEXTAREA'
    || tag === 'SELECT'
    || target.closest('[contenteditable="true"], [role="textbox"]') != null
}

const scrollEntryIntoView = (entryId: string | number) => {
  const root = entriesContainer.value
  if (!root) return
  const el = root.querySelector(`[data-entry-id="${String(entryId)}"]`)
  if (el instanceof HTMLElement) {
    el.scrollIntoView({ block: 'nearest' })
  }
}

const stepReadingEntry = (delta: number) => {
  const list = filteredEntries.value
  if (!list.length) return
  const currentId = readingEntry.value ? String(readingEntry.value.id) : null
  const index = currentId
    ? list.findIndex((entry) => String(entry.id) === currentId)
    : -1
  const nextIndex = nextEntryIndex(list.length, index, delta)
  if (nextIndex < 0) return
  const next = list[nextIndex]
  if (!next) return
  if (currentId && String(next.id) === currentId) return
  openReader(next)
  nextTick(() => scrollEntryIntoView(next.id))
}

const handleWorkspaceKeyDown = (event: KeyboardEvent) => {
  // Lightbox and other reader chrome first.
  handleKeyDown(event)
  if (event.defaultPrevented || event.isComposing || isTypingTarget(event.target)) return

  if (event.key === 'Escape') {
    if (showReaderSettings.value) {
      event.preventDefault()
      showReaderSettings.value = false
      return
    }
    if (readingEntry.value) {
      event.preventDefault()
      readingEntry.value = null
      return
    }
  }

  // Entry list keyboard navigation (j/k and arrows).
  if (event.key === 'j' || event.key === 'J' || event.key === 'ArrowDown') {
    event.preventDefault()
    stepReadingEntry(1)
    return
  }
  if (event.key === 'k' || event.key === 'K' || event.key === 'ArrowUp') {
    event.preventDefault()
    stepReadingEntry(-1)
    return
  }

  if (!readingEntry.value) return

  if (event.key === 's' || event.key === 'S') {
    event.preventDefault()
    void toggleStarStatus(readingEntry.value)
    return
  }
  if (event.key === 'm' || event.key === 'M') {
    event.preventDefault()
    void toggleReadStatus(readingEntry.value)
  }
}

const showUnsubscribeConfirm = ref(false)
const feedToUnsubscribe = ref<RssFeed | null>(null)
const unsubscribingFeed = ref(false)

const requestUnsubscribeFeed = (feed: RssFeed) => {
  closeContextMenu()
  feedToUnsubscribe.value = feed
  showUnsubscribeConfirm.value = true
}

const requestUnsubscribeByEntry = (entry: RssEntry) => {
  const feed = findFeedByEntry(entry.feed_id)
  if (!feed) {
    onStatus('未找到对应的订阅源', true)
    return
  }
  requestUnsubscribeFeed(feed)
}

const confirmUnsubscribeFeed = async () => {
  const feed = feedToUnsubscribe.value
  if (!feed || unsubscribingFeed.value) return
  unsubscribingFeed.value = true
  try {
    const removed = await handleUnsubscribeFeed(feed)
    if (!removed) return
    if (readingEntry.value?.feed_id === feed.id) readingEntry.value = null
    showUnsubscribeConfirm.value = false
    feedToUnsubscribe.value = null
  } finally {
    unsubscribingFeed.value = false
  }
}

const selectAccount = async (accountId: number) => {
  if (selectedAccountId.value === accountId) return
  selectedAccountId.value = accountId
  await nextTick()
  await Promise.all([
    loadFeeds(),
    loadEntries(true),
  ])
  await resumeSyncPollingIfRunning()
}

// Watchers
watch(selectedAccountId, (accountId, previousAccountId) => {
  if (accountId === previousAccountId) return
  stopSyncPolling()
  onStatus('')
  selectedFeedId.value = null
  readingEntry.value = null
  clearFeedNavStack()
  feedSearch.value = ''
  activeFilter.value = 'all'
  collapsedFolders.value = {}
  showReaderSettings.value = false
  showUnsubscribeConfirm.value = false
  feedToUnsubscribe.value = null
  closeContextMenu()
})

// Lifecycle
let releaseInternalBack: (() => void) | null = null

onMounted(async () => {
  window.addEventListener('keydown', handleWorkspaceKeyDown)
  releaseInternalBack = appNavigation.registerInternalBackHandler(handleFeedBack)
  await loadAll()
  nextTick(() => {
    initObserver()
  })
  await resumeSyncPollingIfRunning()
  loadRecentlyViewed()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleWorkspaceKeyDown)
  stopSyncPolling()
  disposeStatus()
  releaseInternalBack?.()
  releaseInternalBack = null
  clearFeedNavStack()
})
</script>

<style scoped>
.rss-workspace {
  --app-workbench-header-height: 3.25rem;
}

.rss-source-controls {
  background: transparent;
}

.rss-source-pane-toggle {
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground) / 0.82);
}

.rss-source-pane-toggle:hover {
  color: hsl(var(--foreground));
}

.rss-add-account-button {
  border-color: hsl(var(--border) / 0.58);
  background: hsl(var(--accent) / 0.24);
  color: hsl(var(--foreground) / 0.82);
}

.rss-add-account-button:hover {
  border-color: hsl(var(--border) / 0.78);
  background: hsl(var(--accent) / 0.58);
  color: hsl(var(--foreground));
}

.rss-sync-status {
  display: flex;
  align-items: center;
  gap: 0.4375rem;
  min-height: 2rem;
  padding-left: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.88);
  font-size: 0.75rem;
}

.rss-sync-status__indicator {
  width: 0.375rem;
  height: 0.375rem;
  flex: 0 0 auto;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.42);
}

.rss-sync-status.is-active .rss-sync-status__indicator {
  background: hsl(var(--foreground) / 0.72);
  box-shadow: 0 0 0 3px hsl(var(--foreground) / 0.08);
}

.rss-sync-status.is-error .rss-sync-status__indicator {
  background: hsl(var(--destructive));
  box-shadow: 0 0 0 3px hsl(var(--destructive) / 0.1);
}

.rss-sync-status__copy {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-sync-status.is-active .rss-sync-status__copy {
  color: hsl(var(--foreground) / 0.82);
}

.rss-sync-status.is-error .rss-sync-status__copy {
  color: hsl(var(--destructive));
}

.rss-sync-status__menu {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.125rem;
  margin-left: auto;
}

.rss-sync-status__menu-btn {
  color: hsl(var(--muted-foreground));
}

.rss-sync-status__menu-btn:hover {
  color: hsl(var(--foreground));
}

.rss-entry-pane {
  --app-pane-list-width: clamp(20rem, 34cqi, 30rem);
  background: transparent;
}

@container workbench (max-width: 68rem) {
  .rss-entry-pane {
    --app-pane-list-width: clamp(19rem, 32cqi, 23rem);
  }

  .rss-reader-toolbar__domain {
    display: none;
  }
}

.rss-entry-list {
  padding: 0;
  background: transparent;
}

.rss-entry-list__inner {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding: 0;
}

.rss-entry-header {
  gap: var(--space-2);
  padding: var(--space-3);
  background: transparent;
}

.rss-entry-header__identity {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  gap: var(--space-2);
}

.rss-back-button {
  flex: none;
  color: hsl(var(--muted-foreground));
}

.rss-entry-tools {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  width: 100%;
}

.rss-filter-tabs {
  width: 100%;
}

.rss-filter-tabs :deep(.app-segmented-control__item) {
  gap: 0.3rem;
  flex: 1;
  min-width: 0;
  padding-inline: 0.375rem;
}

.rss-reader-toolbar {
  justify-content: center;
  min-height: var(--app-workbench-header-height);
  padding: 0 var(--space-4);
  background: transparent;
}

.rss-reader-toolbar__row {
  width: 100%;
  max-width: var(--app-content-reading-max);
  margin-inline: auto;
}

.rss-reader-body {
  padding: clamp(1.25rem, 2.5vh, 2rem) clamp(1.25rem, 3.5vw, 3rem) 5rem;
  background: hsl(var(--background));
}

.rss-entry-stack {
  display: flex;
  flex-direction: column;
}

.rss-entry-skeleton-list {
  display: flex;
  flex-direction: column;
}

.rss-entry-load-more {
  display: flex;
  min-height: 4rem;
  align-items: center;
  justify-content: center;
}

.rss-entry-load-more__status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.6875rem;
}

.rss-entry-item {
  position: relative;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  gap: 0;
  width: 100%;
  min-height: 0;
  padding: 0.875rem 1rem;
  text-align: left;
  outline: none;
}

.rss-entry-stack :deep(.app-selectable-list-item--flush.is-selected) {
  background: hsl(var(--foreground) / 0.035);
  box-shadow: none;
}

.rss-entry-stack :deep(.app-selectable-list-item--flush:not(.is-selected):hover),
.rss-entry-stack :deep(.app-selectable-list-item--flush:not(.is-selected):focus-visible) {
  background: hsl(var(--foreground) / 0.025);
}

.rss-entry-item__meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-width: 0;
  margin-bottom: 0.5rem;
}

.rss-entry-item__source {
  justify-content: flex-start;
  gap: 0.375rem;
  min-width: 0;
  max-width: calc(100% - 5.5rem);
  height: auto;
  padding: 0;
  color: hsl(var(--muted-foreground) / 0.9);
  font-size: 0.75rem;
  font-weight: 600;
}

.rss-entry-item__source:hover {
  background: transparent;
  color: hsl(var(--foreground));
}

.rss-entry-item__source span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-entry-item__status {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.4rem;
}

.rss-entry-item__content {
  min-width: 0;
}

.rss-entry-item__date {
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.rss-entry-item__title {
  min-width: 0;
  margin: 0;
  color: hsl(var(--foreground) / 0.94);
  font-size: 0.9375rem;
  font-weight: 650;
  line-height: 1.4;
  transition: color var(--duration-fast) var(--ease-default);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.rss-entry-item.is-read .rss-entry-item__title {
  color: hsl(var(--muted-foreground) / 0.9);
  font-weight: 550;
}

.rss-entry-item:hover .rss-entry-item__title,
.rss-entry-item:focus-visible .rss-entry-item__title,
.rss-entry-item.is-selected .rss-entry-item__title {
  color: hsl(var(--foreground));
}

.rss-entry-item__summary {
  margin: 0.375rem 0 0;
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.8125rem;
  line-height: 1.5;
  transition: color var(--duration-fast) var(--ease-default);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.rss-entry-item.is-read .rss-entry-item__summary {
  color: hsl(var(--muted-foreground) / 0.7);
}

.rss-entry-item__footer {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
  margin-top: 0.625rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
}

.rss-reader-pane {
  background: hsl(var(--background));
}

.rss-reader-empty {
  display: flex;
  height: 100%;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background: hsl(var(--background));
  text-align: center;
  user-select: none;
}

.rss-reader-active {
  position: relative;
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  background: hsl(var(--background));
}

.rss-reader-toolbar__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.625rem;
}

.rss-reader-source-button {
  min-width: 0;
  max-width: 16rem;
  gap: 0.4375rem;
  padding-inline: 0.375rem;
}

.rss-reader-source-title {
  overflow: hidden;
  max-width: 13rem;
  color: hsl(var(--foreground) / 0.85);
  font-size: 0.6875rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-reader-toolbar__domain {
  overflow: hidden;
  max-width: 12rem;
  color: hsl(var(--muted-foreground) / 0.58);
  font-size: var(--app-text-badge-size);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-reader-actions {
  gap: 0.125rem;
}

.rss-reader-article {
  width: min(100%, 42rem);
  max-width: 42rem;
  margin-inline: auto;
}

.rss-reader-article__header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.22);
}

.rss-reader-article__category {
  display: block;
  margin-bottom: 0.625rem;
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
  font-weight: 650;
}

.rss-reader-title {
  margin: 0;
  color: hsl(var(--foreground) / 0.94);
  cursor: pointer;
  font-family: var(--app-heading-font);
  font-size: clamp(1.55rem, 2.1vw, 1.9rem);
  font-weight: 650;
  letter-spacing: -0.015em;
  line-height: 1.28;
  transition: color var(--duration-fast) var(--ease-default);
  text-wrap: balance;
}

.rss-reader-title:hover {
  color: hsl(var(--foreground) / 0.78);
}

.rss-reader-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  margin-top: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.rss-subscribe-dialog {
  max-width: 28rem;
}

.rss-subscribe-dialog__category-button {
  width: 100%;
  justify-content: space-between;
  padding: 0 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.rss-subscribe-dialog__category-menu {
  margin-top: 0.25rem;
}

.rss-subscribe-dialog__new-category {
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2rem;
  padding: 0 0.625rem;
  color: hsl(var(--foreground) / 0.82);
  font-size: 0.75rem;
  font-weight: 650;
}

.rss-subscribe-dialog__new-category:hover {
  background: hsl(var(--accent) / 0.46);
  color: hsl(var(--foreground));
}

.rss-subscribe-dialog__custom-input {
  padding-right: 2rem;
  padding-left: 0.625rem;
}

.rss-subscribe-dialog__confirm-category {
  position: absolute;
  top: 50%;
  right: 0.25rem;
  width: 1.5rem;
  height: 1.5rem;
  background: hsl(var(--accent) / 0.62);
  color: hsl(var(--foreground));
  transform: translateY(-50%);
}


@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@media (prefers-reduced-motion: reduce) {
  .animate-fade-in {
    animation: none;
  }

  .rss-entry-item {
    transition: none;
  }
}
</style>
