<template>
  <AppPageShell variant="compact" fill>
    <div class="app-workbench rss-workbench">
      <!-- 1. Left Sidebar: Accounts & Feeds -->
      <aside class="app-workbench__sidebar app-workbench__sidebar--always rss-sidebar">
        <!-- Header -->
        <div class="app-workbench__sidebar-header rss-sidebar-header">
          <div class="min-w-0 flex flex-col justify-center">
            <h1 class="app-h2 truncate">RSS 内容源</h1>
            <p class="mt-0.5 text-xs font-medium text-muted-foreground/70">{{ accounts.length }} 个服务账号</p>
          </div>
          <Button
            size="icon-sm"
            @click="openAddAccount"
          >
            <AppIcon name="plus" class="h-5 w-5" />
          </Button>
        </div>

        <!-- Controls: Dropdown & Search -->
        <div class="app-pane__controls">
          <div ref="accountDropdownRef">
            <AccountDropdown
              :accounts="accounts"
              :selected-id="selectedAccountId"
              :selected-name="selectedAccount?.name || ''"
              :open="showAccountDropdown"
              @toggle="showAccountDropdown = !showAccountDropdown"
              @select="(id) => { selectAccount(id); showAccountDropdown = false }"
              @edit="(acc) => { openEditAccount(acc); showAccountDropdown = false }"
              @delete="(acc) => { confirmDeleteAccount(acc); showAccountDropdown = false }"
              @add="openAddAccount(); showAccountDropdown = false"
            />
          </div>

          <!-- Selected Account Sync Info -->
          <div 
            v-if="selectedAccount" 
            class="rss-sync-status"
          >
            <span 
              class="truncate pr-1 flex-1 min-w-0"
              :class="{ 'rss-sync-status__text--active': syncing, 'text-destructive': statusError }"
              :title="statusMessage"
            >
              {{ statusMessage || (selectedAccount.last_sync_at ? '同步于 ' + formatDate(selectedAccount.last_sync_at) : '从未同步') }}
            </span>
            <div class="relative flex items-center gap-0.5 shrink-0" ref="syncDropdownRef">
              <Button
                variant="ghost"
                size="xs"
                @click="syncSelectedAccount(false)"
                class="rss-sync-status__button"
                :disabled="syncing"
              >
                <AppSpinner v-if="syncing" size="sm" />
                <AppIcon v-else name="refresh" class="h-3 w-3" />
                <span>轻量</span>
              </Button>
              <Button
                variant="ghost"
                size="icon-xs"
                @click="showSyncMenu = !showSyncMenu"
                :disabled="syncing"
                aria-label="更多同步选项"
              >
                <AppIcon name="chevronDown" class="h-3 w-3" />
              </Button>
              <AppFloatingList v-if="showSyncMenu" class="rss-sync-menu">
                <Button
                  variant="ghost"
                  size="sm"
                  @click="syncSelectedAccount(true); showSyncMenu = false"
                  class="w-full justify-start"
                >
                  <AppIcon name="refresh" class="h-3 w-3" />
                  <span>全量同步</span>
                </Button>
              </AppFloatingList>
            </div>
          </div>

          <!-- Feed Search input -->
          <div class="relative group">
            <AppIcon name="search" class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary pointer-events-none" />
            <Input
              v-model="feedSearch"
              type="text"
              placeholder="搜索订阅源..."
              aria-label="搜索订阅源"
              class="h-8 pl-7 text-xs rounded-lg"
            />
          </div>
        </div>

        <FeedFolderTree
          :folders="feedFolders"
          :expanded-folders="collapsedFolders"
          :selected-feed-id="selectedFeedId"
          :total-feeds="filteredFeeds.length"
          :has-account="!!selectedAccount"
          @select-all="selectedFeedId = null; loadEntries(true)"
          @add-feed="showSubscribeModal = true"
          @toggle-folder="toggleFolder"
          @select-feed="selectFeed"
          @feed-context-menu="showFeedContextMenu"
          @unsubscribe-feed="handleUnsubscribeFeed"
        />
      </aside>

      <!-- 2. Middle Column: Article List Flow -->
      <section class="app-pane rss-entry-pane">
        <header class="app-pane__header rss-entry-header">
          <div class="flex items-center justify-between w-full">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <Button
                  v-if="hasFeedNavStack"
                  variant="outline"
                  size="xs"
                  class="rss-back-button"
                  title="返回之前的列表"
                  aria-label="返回之前的列表"
                  @click="handleFeedBack"
                >
                  <AppIcon name="back" class="h-3 w-3" />
                  <span>返回</span>
                </Button>
                <h2 class="app-h3 truncate">
                  {{ selectedFeedTitle || selectedAccount?.name || 'RSS 阅读器' }}
                </h2>
              </div>
              <div class="rss-entry-header__subtitle">
                <span>{{ selectedFeedSubtitle }}</span>
                <div v-if="loading" class="flex items-center gap-1 ml-1">
                  <AppBounceDots />
                </div>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon-sm"
              :disabled="loading"
              title="刷新文章"
              aria-label="刷新文章"
              @click="loadAll"
            >
              <AppSpinner v-if="loading" size="sm" />
              <AppIcon v-else name="refresh" class="h-3.5 w-3.5" />
            </Button>
          </div>

          <!-- Controls Toolbar Row -->
          <div class="flex flex-col gap-2 mt-3 w-full">
            <!-- Entry Search -->
            <div class="relative w-full group">
              <AppIcon name="search" class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary pointer-events-none" />
              <Input
                v-model="entrySearch"
                type="text"
                placeholder="搜索文章..."
                aria-label="搜索文章"
                class="h-8 pl-7 text-xs rounded-lg"
              />
            </div>

            <AppSegmentedControl
              v-model="activeFilter"
              :options="rssFilterOptions"
              aria-label="文章筛选"
              size="sm"
              class="rss-filter-tabs"
            />
          </div>
        </header>

        <!-- Main Body Scroll Container -->
        <div ref="entriesContainer" class="min-h-0 flex-1 overflow-y-auto overscroll-contain custom-scrollbar bg-background">
          <div class="w-full p-4 space-y-4">

            <div
              v-if="loading && filteredEntries.length === 0"
              class="app-page-empty app-page-empty--compact flex-col text-center"
            >
              <AppSpinner size="lg" />
            </div>

            <!-- Empty view -->
            <div v-else-if="filteredEntries.length === 0" class="app-page-empty app-page-empty--compact">
              <AppEmptyState
                variant="plain"
                icon="inbox"
                :title="activeFilter === 'recent' ? '暂无浏览记录' : '暂无相关文章'"
                :copy="activeFilter === 'recent' ? '浏览文章后，这里会记录您最近看过的内容。' : (selectedAccount ? '当前无对应文章，可点击同步获取最新内容。' : '请先添加并选择您的 RSS 账号。')"
              />
            </div>

            <!-- Articles List -->
            <div v-else class="app-divider-top app-divider-bottom flex flex-col divide-y divide-border/10">
              <button
                v-for="entry in filteredEntries"
                :key="entry.id"
                type="button"
                class="rss-entry-item group"
                :class="readingEntry && String(readingEntry.id) === String(entry.id) ? 'bg-primary/5' : 'bg-transparent hover:bg-accent/5'"
                :aria-label="entry.is_read ? `已读：${entry.title}` : `未读：${entry.title}`"
                @click="openReader(entry)"
                @contextmenu.prevent.stop="showArticleContextMenu(entry, $event)"
              >
                <!-- Card Top: Category & Time -->
                <div class="rss-entry-item__meta-row">
                  <span class="rss-entry-item__category-row">
                    <span
                      v-if="!entry.is_read"
                      class="rss-entry-item__unread-dot"
                      aria-hidden="true"
                    />
                    <span
                      class="rss-entry-item__category"
                      :class="entry.is_read ? 'text-muted-foreground/55' : 'text-primary'"
                    >
                      {{ getFeedCategory(entry.feed_id) }}
                    </span>
                  </span>
                  <div class="flex items-center gap-1.5">
                    <AppIcon v-if="entry.is_starred" name="star" class="h-3 w-3 text-warning fill-warning" />
                    <span class="rss-entry-item__date">{{ activeFilter === 'recent' ? formatRelativeTime((entry as RecentEntry).viewed_at) : formatDate(entry.published_at) }}</span>
                  </div>
                </div>

                <!-- Title & Summary -->
                <div class="flex-1 space-y-1 mb-3 text-left">
                  <h4
                    class="rss-entry-item__title"
                    :class="[
                      readingEntry && String(readingEntry.id) === String(entry.id)
                        ? 'text-primary'
                        : entry.is_read
                          ? 'text-muted-foreground/75 group-hover:text-foreground/80'
                          : 'text-foreground/90 group-hover:text-primary font-semibold',
                    ]"
                  >
                    {{ entry.title }}
                  </h4>
                  <p
                    v-if="entry.summary"
                    class="rss-entry-item__summary"
                    :class="entry.is_read ? 'text-muted-foreground/50' : 'text-muted-foreground/70'"
                  >{{ stripHtmlTags(entry.summary) }}</p>
                </div>

                <!-- Card Bottom: Source & Media indicator (clickable to view feed) -->
                <div class="flex items-center pt-1">
                  <Button
                    variant="ghost"
                    size="xs"
                    type="button"
                    @click.stop="pushFeedNavStack(); selectFeed(entry.feed_id)"
                    class="rss-feed-link"
                  >
                    <SiteIcon :icon-url="getFeedIconUrl(entry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
                    <span
                      class="text-xs font-semibold truncate transition-colors"
                      :class="entry.is_read ? 'text-muted-foreground/55' : 'text-muted-foreground/90'"
                    >
                      {{ getFeedTitle(entry.feed_id) }}
                    </span>
                  </Button>
                </div>
              </button>
            </div>

            <!-- Infinite Scroll Loader Anchor -->
            <div ref="loadMoreTrigger" class="h-20 flex items-center justify-center w-full">
              <AppSpinner v-if="loadingMoreEntries" />
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Right Column: Permanent Article Content Reader -->
      <main class="app-pane app-pane--fluid rss-reader-pane">
        <!-- If an article is selected, render it -->
        <div v-if="readingEntry" class="rss-reader-active">
          <!-- Reader Header (Clean compact toolbar) -->
          <header class="app-divider-bottom relative z-20 flex h-14 shrink-0 items-center justify-between bg-background px-6">
            <!-- Left Side: Source badge (clickable to view feed) -->
            <Button
              variant="ghost"
              size="xs"
              @click="pushFeedNavStack(); selectFeed(readingEntry.feed_id)"
              class="rss-reader-source-button"
              title="查看该订阅源的所有文章"
            >
              <SiteIcon :icon-url="getFeedIconUrl(readingEntry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
              <span class="font-bold text-foreground/85 truncate max-w-[180px] lg:max-w-[240px]" :title="getFeedTitle(readingEntry.feed_id)">
                {{ getFeedTitle(readingEntry.feed_id) }}
              </span>
            </Button>

            <!-- Right Side: Action buttons -->
            <div class="flex items-center gap-1 shrink-0">
              <!-- 应用内预览原文 -->
              <Button
                variant="ghost"
                size="icon-sm"
                title="在应用内打开原文"
                aria-label="在应用内打开原文"
                @click="openInAppBrowser"
              >
                <AppIcon name="siteFallback" class="h-4 w-4" />
              </Button>

              <!-- 在系统浏览器打开 -->
              <Button as-child variant="ghost" size="icon-sm">
                <a
                  :href="readingEntry.canonical_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  title="在系统浏览器打开"
                  aria-label="在系统浏览器打开"
                >
                  <AppIcon name="externalLink" class="h-4 w-4" />
                </a>
              </Button>

              <!-- 收藏 / 取消收藏 -->
              <Button
                variant="ghost"
                size="icon-sm"
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
                variant="ghost"
                size="icon-sm"
                class="hover:bg-destructive/10 hover:text-destructive"
                title="取消订阅该源"
                aria-label="取消订阅该源"
                @click="unsubscribeCurrentFeedFromReader"
              >
                <AppIcon name="close" class="h-4 w-4" />
              </Button>

              <!-- Reader Settings -->
              <div class="relative" ref="readerSettingsRef">
                <Button
                  variant="ghost"
                  size="icon-sm"
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
                  @update:font-size="readerFontSize = $event"
                  @save="saveReaderPrefs()"
                />
              </div>
            </div>
          </header>
          
          <!-- Reader Body Scroll Container -->
          <div 
            ref="readerScrollContainer"
            class="min-h-0 flex-1 overflow-y-auto overscroll-contain custom-scrollbar px-5 md:px-16 lg:px-28 py-8 bg-background relative"
          >
            <!-- Editorial Header -->
            <div class="app-reader-width mb-8">
              <!-- Title -->
              <h1 
                @click="openInAppBrowser"
                class="text-xl md:text-2xl font-bold text-foreground/90 hover:text-primary leading-relaxed cursor-pointer transition-colors duration-200"
                title="点击在应用内打开原文"
              >
                {{ readingEntry.title }}
              </h1>

              <!-- Date -->
              <div class="mt-2 text-xs text-muted-foreground/50 tabular-nums">
                {{ formatDate(readingEntry.published_at) }}
              </div>
            </div>

            <!-- Content -->
            <div 
              class="reader-content app-reader-width prose prose-neutral dark:prose-invert text-foreground/80 py-2 space-y-0"
              :class="readerFontClass"
              :style="{ fontSize: readerFontSize + 'px' }"
              @click="handleContentClick"
              v-html="cleanAndDecodeHtml(readingEntry.summary) || '<p class=text-muted-foreground>该文章暂无正文内容。</p>'"
            />
          </div>

          <!-- Reeder-style Slide-over In-App Browser Overlay -->
          <div 
            v-if="showInAppBrowser"
            class="rss-browser-overlay"
          >
            <!-- Browser Toolbar -->
            <header class="rss-browser-toolbar">
              <!-- Left Side: Back/Close button -->
              <div class="flex items-center gap-3 min-w-0">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  @click="showInAppBrowser = false"
                  class="rss-browser-toolbar__button"
                  title="返回正文"
                >
                  <AppIcon name="back" class="h-4 w-4" />
                </Button>
                <div class="flex flex-col min-w-0 leading-tight">
                  <span class="rss-browser-toolbar__label">正在浏览原文</span>
                  <span class="text-xs font-semibold text-foreground/80 truncate max-w-[150px] lg:max-w-[280px]">
                    {{ readingEntry.title }}
                  </span>
                </div>
              </div>

              <!-- Center: Address Bar (Globe + Domain) -->
              <div class="rss-browser-address">
                <AppIcon name="siteFallback" class="h-3.5 w-3.5 mr-1.5 text-muted-foreground/60 shrink-0" />
                <span class="truncate">{{ getDisplayDomain(readingEntry.canonical_url) }}</span>
              </div>

              <!-- Right Side: Navigation & Refresh -->
              <div class="flex items-center gap-2 shrink-0">
                <!-- 刷新 -->
                <Button
                  variant="ghost"
                  size="icon-sm"
                  @click="refreshIframe"
                  class="rss-browser-toolbar__button"
                  title="重新加载"
                >
                  <AppSpinner v-if="iframeLoading" size="sm" muted />
                  <AppIcon v-else name="refresh" class="h-4 w-4" />
                </Button>

                <!-- 在系统浏览器打开 -->
                <Button as-child variant="ghost" size="icon-sm" class="rss-browser-toolbar__button">
                  <a
                    :href="readingEntry.canonical_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    title="在系统浏览器打开"
                  >
                    <AppIcon name="externalLink" class="h-4 w-4" />
                  </a>
                </Button>
              </div>
            </header>

            <!-- Iframe Webview Body -->
            <div class="flex min-h-0 flex-1 w-full overflow-hidden bg-background relative flex-col">
              <iframe 
                :key="iframeLoadKey"
                ref="iframeRef"
                :src="readingEntry.canonical_url"
                :data-load-key="iframeLoadKey"
                class="w-full h-full border-0 bg-white"
                @load="handleIframeLoad"
              />
              
              <!-- Fallback Browser Alert for web users -->
              <div v-if="!isElectron && !iframeLoading" class="rss-browser-alert">
                <span class="font-bold text-foreground">原文加载提示</span>
                <span class="text-muted-foreground">如果页面显示空白或拒绝连接，是由于源站安全策略限制。您可以点击右上角图标在外部浏览器中打开。</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- If no article is selected, render a neutral placeholder -->
        <div v-else class="rss-reader-empty">
          <AppEmptyState
            variant="plain"
            icon="library"
            title="选择文章开始阅读"
            copy="从中间列表挑选感兴趣的文章，或在右侧搜索特定内容。"
          />
        </div>
      </main>
    </div>

    <!-- 3. Add / Edit RSS Account Dialog -->
    <AccountEditDialog
      v-model:open="showAddEditModal"
      v-model:form="accountForm"
      :providers="providers"
      :base-url-placeholder="baseUrlPlaceholder"
      :credential-placeholder="credentialPlaceholder"
      :form-message="formMessage"
      :form-error="formError"
      :can-save-form="canSaveForm"
      :can-test-form="canTestForm"
      :saving="saving"
      :testing="testing"
      @save="saveAccount"
      @test="testForm"
    />

    <!-- 4. Delete Account Confirmation Dialog -->
    <DeleteAccountDialog
      v-model:open="showDeleteConfirmModal"
      :account-name="accountToDelete?.name || ''"
      @confirm="handleDeleteAccount"
    />

    <Dialog :open="showSubscribeModal" @update:open="showSubscribeModal = $event">
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
              <Input
                v-model="subscribeForm.feedUrl"
                class="app-form-input app-form-input--with-icon"
                placeholder="https://example.com/rss/feed.xml"
              />
            </div>
          </div>

          <div class="app-dialog-form-field" ref="categoryDropdownRef">
            <label class="app-dialog-form-label">分类</label>
            <Button
              variant="outline"
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
                  variant="ghost"
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
                  <Input
                    v-model="subscribeForm.customCategory"
                    class="app-form-input rss-subscribe-dialog__custom-input"
                    placeholder="输入分类名称"
                    @keyup.enter="confirmCustomCategory"
                    ref="customCategoryInputRef"
                  />
                  <Button
                    variant="ghost"
                    size="mini-icon"
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
            variant="outline"
            class="app-dialog-button"
            @click="closeSubscribeModal"
          >
            取消
          </Button>
          <Button
            type="button"
            class="app-dialog-button app-dialog-button--primary"
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
      :ref="bindArticleMenuRef"
      @toggle-read="toggleReadStatus"
      @toggle-star="toggleStarStatus"
      @go-to-feed="goToFeedFromContextMenu"
      @set-open-method="(feed, method) => setFeedOpenMethod(feed, method)"
      @batch-read="(scope, read) => batchUpdateReadStatus(scope, read)"
      @unsubscribe="unsubscribeCurrentFeed"
      @copy-link="copyArticleLink"
      @open-external="openInExternalBrowser"
      @close="closeContextMenu"
    />

    <!-- Customized Feed Right-Click Context Menu -->
    <RssFeedContextMenu
      :visible="showFeedContextMenuState"
      :feed="contextMenuFeed"
      :position="feedContextMenuPosition"
      :ref="bindFeedMenuRef"
      @mark-all-read="markFeedAllAsRead"
      @sync-feed="syncFeedFromContextMenu"
      @copy-link="copyFeedLink"
      @open-site="openFeedSiteInExternalBrowser"
      @set-open-method="(feed, method) => setFeedOpenMethod(feed, method)"
      @unsubscribe="unsubscribeFeedFromContextMenu"
      @close="closeFeedContextMenu"
    />
  </AppPageShell>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppBounceDots from '@/shared/components/AppBounceDots.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import ReaderSettingsPanel from '@/features/rss/components/ReaderSettingsPanel.vue'
import AccountDropdown from '@/features/rss/components/AccountDropdown.vue'
import FeedFolderTree from '@/features/rss/components/FeedFolderTree.vue'
import AccountEditDialog from '@/features/rss/components/AccountEditDialog.vue'
import DeleteAccountDialog from '@/features/rss/components/DeleteAccountDialog.vue'
import RssImageLightbox from '@/features/rss/components/RssImageLightbox.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListEmpty from '@/shared/components/layout/AppListEmpty.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import AppListSeparator from '@/shared/components/layout/AppListSeparator.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import { formatDate } from '@/shared/lib/dateFormat'
import { useRssAccounts } from '@/features/rss/composables/useRssAccounts'
import { useRssFeeds } from '@/features/rss/composables/useRssFeeds'
import { useRssEntries } from '@/features/rss/composables/useRssEntries'
import { useRssReader } from '@/features/rss/composables/useRssReader'
import { useRssSync } from '@/features/rss/composables/useRssSync'
import { useRssStatus } from '@/features/rss/composables/useRssStatus'
import { useRssFeedHeader } from '@/features/rss/composables/useRssFeedHeader'
import { useRssContextMenu } from '@/features/rss/composables/useRssContextMenu'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import RssFeedContextMenu from '@/features/rss/components/RssFeedContextMenu.vue'
import RssArticleContextMenu from '@/features/rss/components/RssArticleContextMenu.vue'
import type { RssEntry, RecentEntry } from '@/features/rss/composables/rssTypes'

// Cross-cutting UI state
const loading = ref(false)
const rssFilterOptions = [
  { value: 'all', label: '全部' },
  { value: 'unread', label: '未读' },
  { value: 'starred', label: '星标' },
  { value: 'recent', label: '最近浏览' },
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
  selectedAccountId,
  showAddEditModal,
  showDeleteConfirmModal,
  accountToDelete,
  showAccountDropdown,
  saving,
  testing,
  accountForm,
  formMessage,
  formError,
  selectedAccount,
  baseUrlPlaceholder,
  credentialPlaceholder,
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

const {
  feeds,
  selectedFeedId,
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
  unsubscribeFeedFromContextMenu,
} = useRssFeeds({
  selectedAccountId,
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

  showInAppBrowser,
  iframeLoading,
  iframeLoadKey,
  iframeProgress,
  isElectron,
  iframeRef,
  activeLightboxImg,
  lightboxScale,

  readerFontClass,
  saveReaderPrefs,
  handleContentClick,
  closeLightbox,
  handleKeyDown,
  refreshIframe,
  openInAppBrowser,
  handleIframeLoad,
  cleanAndDecodeHtml,
  stripHtmlTags,
  formatRelativeTime,
  unsubscribeCurrentFeedFromReader,

} = useRssReader({
  selectedAccountId,
  feeds,
  findFeedByEntry,
  getFeedTitle,
  getFeedCategory,
  getFeedIconUrl,
  onStatus,
  onRefreshFeeds: loadFeeds,
  onRefreshEntries: (isReset) => loadEntries(isReset ?? true),
})

const {
  activeFilter,
  entrySearch,
  totalEntries,
  loadingMoreEntries,
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
  getFeedTitle,
  readingEntry,
  onStatus,
})

// 单一来源仍是 useNavigationHistory：RSS 内部的 "feed → feed" 二级栈
// 通过 registerInternalBackHandler 暴露给全局，让 AppHeader.back 按钮、
// Alt+← 快捷键、页内"返回"按钮三个入口行为完全一致。
const appNavigation = useNavigationHistory()

const handleFeedBack = (): boolean => goBackFromFeed()

// ponytail: sync polling owns its own state + onClickOutside + timer cleanup;
// injects selectedAccountId, onStatus, and the three completion loaders.
const {
  syncing,
  showSyncMenu,
  syncDropdownRef,
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
  await loadAccounts()
  await loadFeeds()
  await loadEntries(true)
  loading.value = false
}

const loadAll = loadAllImpl

const openReader = (entry: RssEntry) => {
  readingEntry.value = entry
  showInAppBrowser.value = false
  iframeLoading.value = false
  resetIframeState()

  const feed = findFeedByEntry(entry.feed_id)
  const method = feed?.open_method

  if (method === 'external_browser') {
    window.open(entry.canonical_url, '_blank')
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
    nextTick(() => openInAppBrowser())
  }
}

const resetIframeState = () => {
  iframeProgress.value = 0
}

const unsubscribeCurrentFeed = async (entry: RssEntry) => {
  const feed = findFeedByEntry(entry.feed_id)
  if (!feed) {
    onStatus('未找到对应的订阅源', true)
    return
  }
  entriesCloseContextMenu()
  await handleUnsubscribeFeed(feed)
}

const selectAccount = async (accountId: number) => {
  selectedAccountId.value = accountId
  selectedFeedId.value = null
  await loadFeeds()
  await loadEntries(true)
}

// Watchers
watch(selectedAccountId, () => {
  collapsedFolders.value = {}
})

// Lifecycle
let releaseInternalBack: (() => void) | null = null

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  releaseInternalBack = appNavigation.registerInternalBackHandler(handleFeedBack)
  await loadAll()
  nextTick(() => {
    initObserver()
  })
  await resumeSyncPollingIfRunning()
  loadRecentlyViewed()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  stopSyncPolling()
  disposeStatus()
  releaseInternalBack?.()
  releaseInternalBack = null
  clearFeedNavStack()
})
</script>

<style scoped>
.rss-workbench {
  selection-color: hsl(var(--foreground));
}

.rss-sidebar {
  --app-workbench-sidebar-width: 20rem;
}

.rss-sidebar-header {
  --app-workbench-header-height: 4.75rem;
}

.rss-sync-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  border: 1px solid hsl(var(--border) / 0.45);
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.24);
  padding: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.rss-sync-status__text--active {
  color: hsl(var(--primary));
  font-weight: 650;
}

.rss-entry-pane {
  width: 25rem;
}

.rss-entry-header {
  padding: 0.875rem;
}

.rss-back-button {
  flex: none;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 700;
}

.rss-filter-tabs {
  width: 100%;
}

.rss-filter-tabs :deep(.app-segmented-control__item) {
  flex: 1;
}

.rss-entry-item {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 100%;
  padding: 1rem 0.875rem;
  background: transparent;
  border: 0;
  text-align: left;
  cursor: pointer;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.rss-entry-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.35);
}

.rss-sync-status__button {
  flex: 0 0 auto;
  gap: 0.25rem;
  color: hsl(var(--primary));
  font-weight: 650;
}

.rss-entry-header__subtitle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground) / 0.8);
  font-size: 0.6875rem;
  font-weight: 500;
}

.rss-entry-item__meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.85);
  font-size: 0.75rem;
}

.rss-entry-item__category-row {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

/* Unread indicator — only colour is not enough (UI-045). Pair the amber dot
   with `font-semibold` on the title + `aria-label="未读：..."` so screen readers
   and monochrome viewers also perceive state. */
.rss-entry-item__unread-dot {
  display: inline-block;
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: hsl(var(--primary));
  flex: 0 0 auto;
}

.rss-entry-item__category {
  display: inline-flex;
  align-items: center;
  font-size: 0.6875rem;
  font-weight: 700;
  transition: color var(--duration-fast) var(--ease-default);
}

.rss-entry-item__date {
  color: hsl(var(--muted-foreground) / 0.6);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.rss-entry-item__title {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.4;
  text-wrap: balance;
  transition: color var(--duration-fast) var(--ease-default);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.rss-entry-item__summary {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.55;
  transition: color var(--duration-fast) var(--ease-default);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.rss-reader-pane {
  border-inline-start: 0;
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

.rss-browser-overlay {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  flex-direction: column;
  border-inline-start: 1px solid hsl(var(--border) / 0.42);
  background: hsl(var(--background));
}

.rss-browser-toolbar {
  position: relative;
  z-index: 20;
  display: flex;
  height: 3.5rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid hsl(var(--border) / 0.38);
  background: hsl(var(--background));
  padding: 0 1.5rem;
}

.rss-browser-toolbar__button {
  flex: 0 0 auto;
  width: 2rem;
  height: 2rem;
  background: hsl(var(--accent) / 0.3);
}

.rss-browser-toolbar__label {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 700;
}

.rss-browser-address {
  position: absolute;
  left: 50%;
  top: 50%;
  display: none;
  max-width: 20rem;
  transform: translate(-50%, -50%);
  align-items: center;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.28);
  padding: 0.25rem 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  font-weight: 600;
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
  color: hsl(var(--primary));
  font-size: 0.75rem;
  font-weight: 650;
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
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  transform: translateY(-50%);
}

@media (min-width: 768px) {
  .rss-browser-address {
    display: flex;
  }
}

.rss-browser-alert {
  position: absolute;
  right: 1rem;
  bottom: 1rem;
  z-index: 20;
  display: flex;
  max-width: 20rem;
  flex-direction: column;
  gap: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: var(--radius-md);
  background: hsl(var(--popover));
  padding: 0.75rem;
  color: hsl(var(--popover-foreground));
  font-size: 0.6875rem;
  line-height: 1.55;
  box-shadow: 0 8px 24px hsl(var(--foreground) / 0.12);
}

.rss-reader-empty {
  display: flex;
  height: 100%;
  flex: 1;
  user-select: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: hsl(var(--background));
  padding: 2rem;
  text-align: center;
}

/* Scoped stylesheet for reader content typography — WeRead-inspired */
.font-serif {
  font-family: Georgia, Cambria, "Times New Roman", Times, "Nimbus Roman No9 L", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
}
.font-sans {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
.font-outfit {
  font-family: Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
.font-lora {
  font-family: Lora, Georgia, Cambria, "Times New Roman", Times, "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
}

.reader-content {
  font-family: var(--reader-font, inherit);
  text-align: justify;
  text-justify: normal;
  word-break: break-word;
  padding-top: 0.5rem;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.reader-content.font-sans {
  --reader-font: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.reader-content.font-outfit {
  --reader-font: Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.reader-content.font-serif {
  --reader-font: Georgia, Cambria, "Times New Roman", Times, "Nimbus Roman No9 L", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
}

.reader-content.font-lora {
  --reader-font: Lora, Georgia, Cambria, "Times New Roman", Times, "Nimbus Roman No9 L", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
}

/* Paragraphs — generous spacing, first-line indent for Chinese (serif fonts only).
   Specificity > Tailwind/Prose preflight, so no `!important` needed.
   First/last-child reset is universal across families. */
.reader-content :deep(p) {
  margin-bottom: 1.25rem;
  letter-spacing: 0.03em;
  color: hsl(var(--foreground) / 0.82);
}

.reader-content.font-serif :deep(p),
.reader-content.font-lora :deep(p) {
  line-height: 2;
  text-indent: 2em;
}

.reader-content :deep(p:first-child),
.reader-content.font-serif :deep(p:first-child),
.reader-content.font-lora :deep(p:first-child) {
  text-indent: 0;
}

.reader-content :deep(p:last-child) {
  margin-bottom: 0;
}

.dark .reader-content :deep(p) {
  color: hsl(var(--foreground) / 0.78);
}

/* Headings — understated, no decoration */
.reader-content :deep(h1) {
  font-size: 1.6em;
  margin-top: 2.5rem;
  margin-bottom: 1.2rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.4;
  color: hsl(var(--foreground) / 0.9);
  text-indent: 0;
}

.reader-content :deep(h2) {
  font-size: 1.3em;
  margin-top: 2.2rem;
  margin-bottom: 1rem;
  font-weight: 600;
  letter-spacing: 0;
  color: hsl(var(--foreground) / 0.88);
  text-indent: 0;
}

.reader-content :deep(h3) {
  font-size: 1.15em;
  margin-top: 1.8rem;
  margin-bottom: 0.8rem;
  font-weight: 600;
  color: hsl(var(--foreground) / 0.85);
  text-indent: 0;
}

.reader-content :deep(h4) {
  font-size: 1.05em;
  margin-top: 1.5rem;
  margin-bottom: 0.6rem;
  font-weight: 600;
  color: hsl(var(--foreground) / 0.82);
  text-indent: 0;
}

/* Links — minimal, color only */
.reader-content :deep(a) {
  color: hsl(var(--primary) / 0.9);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.15s ease;
}

.reader-content :deep(a:hover) {
  color: hsl(var(--primary));
}

/* Lists */
.reader-content :deep(ul),
.reader-content :deep(ol) {
  padding-left: 1.75em;
  margin-bottom: 1.25rem;
}

.reader-content :deep(li) {
  margin-bottom: 0.35rem;
  line-height: 2;
  color: hsl(var(--foreground) / 0.82);
}

.reader-content :deep(li > p) {
  text-indent: 0;
  margin-bottom: 0.35rem;
}

.reader-content :deep(ul > li) {
  list-style-type: none;
  padding-left: 0;
  position: relative;
}

.reader-content :deep(ul > li::before) {
  content: '';
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: hsl(var(--foreground) / 0.25);
  position: absolute;
  left: -0.75em;
  top: 0.7em;
}

.reader-content :deep(ol > li) {
  list-style-type: decimal;
}

/* Images — clean, centered */
.reader-content :deep(img) {
  max-width: 100%;
  max-height: 50vh;
  object-fit: contain;
  border-radius: 4px;
  margin: 1.75rem auto;
  display: block;
}

.dark .reader-content :deep(img) {
  opacity: 0.92;
}

.reader-content :deep(figure) {
  margin: 1.75rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.reader-content :deep(figcaption) {
  font-size: 0.8rem;
  color: hsl(var(--muted-foreground) / 0.7);
  margin-top: 0.5rem;
  text-align: center;
  font-style: normal;
  letter-spacing: 0;
  text-indent: 0;
}

/* Code blocks */
.reader-content :deep(pre) {
  background: hsl(var(--muted) / 0.45);
  border: none;
  border-radius: 4px;
  padding: 1rem 1.25rem;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.7;
  margin: 1.5rem 0;
  text-indent: 0;
}

.reader-content :deep(pre p),
.reader-content.font-serif :deep(pre p),
.reader-content.font-lora :deep(pre p) {
  text-indent: 0;
}

.reader-content :deep(code:not(pre code)) {
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--foreground) / 0.8);
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88em;
  font-weight: 400;
}

/* Blockquotes — left bar, quiet */
.reader-content :deep(blockquote) {
  border: none;
  box-shadow: inset 2px 0 0 hsl(var(--primary) / 0.42);
  padding: 0.5rem 1.25rem;
  margin: 1.5rem 0;
  background: transparent;
  color: hsl(var(--foreground) / 0.65);
  font-size: 0.97em;
  line-height: 2;
  text-indent: 0;
}

.reader-content :deep(blockquote p),
.reader-content.font-serif :deep(blockquote p),
.reader-content.font-lora :deep(blockquote p) {
  text-indent: 0;
  margin-bottom: 0.5rem;
  line-height: 2;
}

.reader-content :deep(blockquote p:last-child),
.reader-content.font-serif :deep(blockquote p:last-child),
.reader-content.font-lora :deep(blockquote p:last-child) {
  margin-bottom: 0;
}

/* Divider — subtle */
.reader-content :deep(hr) {
  border: 0;
  height: 1px;
  background: hsl(var(--border) / 0.4);
  margin: 2rem 0;
}

.reader-content :deep(hr::after) {
  content: none;
}

/* Table handling — no indent */
.reader-content :deep(table) {
  text-indent: 0;
}

.reader-content :deep(th),
.reader-content :deep(td) {
  text-indent: 0;
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
