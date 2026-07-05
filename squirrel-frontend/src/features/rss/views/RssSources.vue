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
              <button 
                @click="syncSelectedAccount(false)" 
                class="rss-sync-status__button"
                :disabled="syncing"
              >
                <AppSpinner v-if="syncing" size="sm" />
                <AppIcon v-else name="refresh" class="h-3 w-3" />
                <span>轻量</span>
              </button>
              <button 
                @click="showSyncMenu = !showSyncMenu" 
                class="p-0.5 rounded text-muted-foreground/60 hover:text-primary transition-colors"
                :disabled="syncing"
              >
                <AppIcon name="chevronDown" class="h-3 w-3" />
              </button>
              <div 
                v-if="showSyncMenu" 
                class="rss-sync-menu"
              >
                <button 
                  @click="syncSelectedAccount(true); showSyncMenu = false" 
                  class="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  <AppIcon name="refresh" class="h-3 w-3" />
                  <span>全量同步</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Feed Search input -->
          <div class="relative group">
            <AppIcon name="search" class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary" />
            <input
              v-model="feedSearch"
              type="text"
              placeholder="搜索订阅源..."
              aria-label="搜索订阅源"
              class="rss-search-input"
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
                <button
                  v-if="feedNavStack"
                  class="rss-back-button"
                  title="返回之前的列表"
                  aria-label="返回之前的列表"
                  @click="goBackFromFeed"
                >
                  <AppIcon name="back" class="h-3 w-3" />
                  <span>返回</span>
                </button>
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
              <AppIcon name="search" class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary" />
              <input
                v-model="entrySearch"
                type="text"
                placeholder="搜索文章..."
                aria-label="搜索文章"
                class="rss-search-input"
              />
            </div>

            <!-- iOS/Reeder segmented control -->
            <div class="app-tab-list rss-filter-tabs">
              <button
                class="app-tab-button rss-filter-tab"
                :class="{ 'is-active': activeFilter === 'all' }"
                :aria-pressed="activeFilter === 'all'"
                @click="activeFilter = 'all'"
              >
                全部
              </button>
              <button
                class="app-tab-button rss-filter-tab"
                :class="{ 'is-active': activeFilter === 'unread' }"
                :aria-pressed="activeFilter === 'unread'"
                @click="activeFilter = 'unread'"
              >
                未读
              </button>
              <button
                class="app-tab-button rss-filter-tab"
                :class="{ 'is-active': activeFilter === 'starred' }"
                :aria-pressed="activeFilter === 'starred'"
                @click="activeFilter = 'starred'"
              >
                星标
              </button>
              <button
                class="app-tab-button rss-filter-tab"
                :class="{ 'is-active': activeFilter === 'recent' }"
                :aria-pressed="activeFilter === 'recent'"
                @click="activeFilter = 'recent'"
              >
                最近浏览
              </button>
            </div>
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
              <div
                v-for="entry in filteredEntries"
                :key="entry.id"
                class="rss-entry-item group"
                :class="readingEntry && String(readingEntry.id) === String(entry.id) ? 'bg-primary/5' : 'bg-transparent hover:bg-accent/5'"
                role="button"
                tabindex="0"
                @click="openReader(entry)"
                @keydown.enter.prevent="openReader(entry)"
                @keydown.space.prevent="openReader(entry)"
                @contextmenu.prevent.stop="showArticleContextMenu(entry, $event)"
              >
                <!-- Card Top: Category & Time -->
                <div class="rss-entry-item__meta-row">
                  <span
                    class="rss-entry-item__category"
                    :class="entry.is_read ? 'text-muted-foreground/55' : 'text-primary'"
                  >
                    {{ getFeedCategory(entry.feed_id) }}
                  </span>
                  <div class="flex items-center gap-1.5">
                    <AppIcon v-if="entry.is_starred" name="star" class="h-3 w-3 text-warning fill-warning" />
                    <span class="rss-entry-item__date">{{ activeFilter === 'recent' ? formatRelativeTime((entry as RecentEntry).viewed_at) : formatDate(entry.published_at) }}</span>
                  </div>
                </div>
                
                <!-- Title & Summary -->
                <div class="flex-1 space-y-1 mb-3">
                  <h4
                    class="text-xs font-bold leading-snug transition-colors duration-200 ease-out line-clamp-2"
                    :class="readingEntry && String(readingEntry.id) === String(entry.id)
                      ? 'text-primary'
                      : entry.is_read
                        ? 'text-muted-foreground/75 group-hover:text-foreground/80'
                        : 'text-foreground/90 group-hover:text-primary'"
                  >
                    {{ entry.title }}
                  </h4>
                  <p
                    v-if="entry.summary"
                    class="text-xs leading-relaxed line-clamp-2 transition-colors"
                    :class="entry.is_read ? 'text-muted-foreground/50' : 'text-muted-foreground/70'"
                  >{{ stripHtmlTags(entry.summary) }}</p>
                </div>
                
                <!-- Card Bottom: Source & Media indicator (clickable to view feed) -->
                <div class="flex items-center pt-1">
                  <button
                    @click.stop="pushFeedNavStack(); selectFeed(entry.feed_id)"
                    class="flex items-center gap-2 min-w-0 text-left hover:text-primary transition-colors cursor-pointer"
                  >
                    <SiteIcon :icon-url="getFeedIconUrl(entry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
                    <span
                      class="text-xs font-semibold truncate transition-colors"
                      :class="entry.is_read ? 'text-muted-foreground/55' : 'text-muted-foreground/90'"
                    >
                      {{ getFeedTitle(entry.feed_id) }}
                    </span>
                  </button>
                </div>
              </div>
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
            <button
              @click="pushFeedNavStack(); selectFeed(readingEntry.feed_id)"
              class="flex items-center gap-2 text-xs text-muted-foreground/80 min-w-0 pr-4 hover:text-primary transition-colors cursor-pointer"
              title="查看该订阅源的所有文章"
            >
              <SiteIcon :icon-url="getFeedIconUrl(readingEntry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
              <span class="font-bold text-foreground/85 truncate max-w-[180px] lg:max-w-[240px]" :title="getFeedTitle(readingEntry.feed_id)">
                {{ getFeedTitle(readingEntry.feed_id) }}
              </span>
            </button>

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
              <a
                :href="readingEntry.canonical_url"
                target="_blank"
                rel="noopener noreferrer"
                class="app-icon-button"
                title="在系统浏览器打开"
                aria-label="在系统浏览器打开"
              >
                <AppIcon name="externalLink" class="h-4 w-4" />
              </a>

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
                <button 
                  @click="showInAppBrowser = false"
                  class="rss-browser-toolbar__button"
                  title="返回正文"
                >
                  <AppIcon name="back" class="h-4 w-4" />
                </button>
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
                <button 
                  @click="refreshIframe"
                  class="rss-browser-toolbar__button"
                  title="重新加载"
                >
                  <AppSpinner v-if="iframeLoading" size="sm" muted />
                  <AppIcon v-else name="refresh" class="h-4 w-4" />
                </button>

                <!-- 在系统浏览器打开 -->
                <a 
                  :href="readingEntry.canonical_url" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="rss-browser-toolbar__button"
                  title="在系统浏览器打开"
                >
                  <AppIcon name="externalLink" class="h-4 w-4" />
                </a>
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
        
        <!-- If no article is selected, render a gorgeous premium workstation-themed placeholder -->
        <div v-else class="rss-reader-empty">
          <div class="rss-reader-empty-icon">
            <AppIcon name="library" class="h-6 w-6 text-primary/70" />
          </div>
          <p class="text-xs text-muted-foreground max-w-[280px] leading-relaxed">
            选择左侧订阅源，并点击中间文章列表中感兴趣的文章即可开始阅读。
          </p>
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

    <!-- 5. Subscribe Feed Dialog -->
    <Dialog :open="showSubscribeModal" @update:open="showSubscribeModal = $event">
      <DialogContent class="max-w-md !overflow-visible rounded-lg p-0 transition-colors duration-150">
        <DialogHeader class="app-divider-bottom p-5 text-left">
          <DialogTitle class="text-base font-bold text-foreground">添加订阅源</DialogTitle>
          <DialogDescription class="text-xs text-muted-foreground mt-1 leading-normal">
            输入 RSS 订阅源 URL，将其添加到「{{ selectedAccount?.name }}」账号。
          </DialogDescription>
        </DialogHeader>

        <div class="rss-subscribe-dialog__body">
          <!-- Feed URL -->
          <div class="rss-subscribe-dialog__field">
            <label>订阅源 URL</label>
            <div class="rss-subscribe-dialog__input-wrap">
              <AppIcon name="link" class="rss-subscribe-dialog__input-icon" />
              <Input
                v-model="subscribeForm.feedUrl"
                class="rss-subscribe-dialog__input"
                placeholder="https://example.com/rss/feed.xml"
              />
            </div>
          </div>

          <!-- Category (custom dropdown matching app style) -->
          <div class="rss-subscribe-dialog__field" ref="categoryDropdownRef">
            <label>分类</label>
            <button
              @click="showCategoryDropdown = !showCategoryDropdown"
              class="rss-subscribe-dialog__category-button"
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
            </button>

            <div
              v-if="showCategoryDropdown"
              class="rss-subscribe-dialog__category-menu"
            >
              <div class="rss-subscribe-dialog__category-list custom-scrollbar">
                <button
                  @click="subscribeForm.category = ''; showCategoryDropdown = false"
                  class="rss-subscribe-dialog__category-option"
                  :class="!subscribeForm.category ? 'text-foreground bg-accent/50 font-semibold' : 'text-muted-foreground'"
                >
                  <span>未分类</span>
                </button>
                <button
                  v-for="cat in existingCategories"
                  :key="cat"
                  @click="subscribeForm.category = cat; showCategoryDropdown = false"
                  class="rss-subscribe-dialog__category-option"
                  :class="subscribeForm.category === cat ? 'text-foreground bg-accent/50 font-semibold' : 'text-muted-foreground'"
                >
                  <span>{{ cat }}</span>
                </button>
                <div v-if="!existingCategories.length" class="rss-subscribe-dialog__empty">暂无分类</div>
              </div>
              <div class="rss-subscribe-dialog__separator"></div>
              <div v-if="!showCustomCategoryInput" class="p-1">
                <button
                  @click="showCustomCategoryInput = true"
                  class="rss-subscribe-dialog__new-category"
                >
                  <AppIcon name="plus" class="h-3.5 w-3.5" />
                  新建分类
                </button>
              </div>
              <div v-else class="p-2">
                <div class="relative">
                  <Input
                    v-model="subscribeForm.customCategory"
                    class="rss-subscribe-dialog__custom-input"
                    placeholder="输入分类名称"
                    @keyup.enter="confirmCustomCategory"
                    ref="customCategoryInputRef"
                  />
                  <button
                    @click="confirmCustomCategory"
                    class="rss-subscribe-dialog__confirm-category"
                  >
                    <AppIcon name="check" class="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Error / Success Message -->
          <Transition name="fade">
            <div
              v-if="subscribeMessage"
              class="rss-subscribe-dialog__message"
              :class="subscribeError ? 'border-destructive/20 bg-destructive/5 text-destructive' : 'border-emerald-500/20 bg-success/5 text-success'"
            >
              <AppIcon
                :name="subscribeError ? 'error' : 'check'"
                class="h-3.5 w-3.5 shrink-0 mt-0.5"
                :class="subscribeError ? 'text-destructive' : 'text-success'"
              />
              <span class="font-medium">{{ subscribeMessage }}</span>
            </div>
          </Transition>
        </div>

        <DialogFooter class="rss-subscribe-dialog__footer">
          <Button
            type="button"
            variant="outline"
            class="rss-subscribe-dialog__button"
            @click="closeSubscribeModal"
          >
            取消
          </Button>
          <Button
            type="button"
            class="rss-subscribe-dialog__button rss-subscribe-dialog__button--primary"
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
import RssFeedContextMenu from '@/features/rss/components/RssFeedContextMenu.vue'
import RssArticleContextMenu from '@/features/rss/components/RssArticleContextMenu.vue'
import type { RssEntry, RecentEntry } from '@/features/rss/composables/rssTypes'

// Cross-cutting UI state
const loading = ref(false)

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
  feedNavStack,
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
onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('click', closeContextMenu)
  window.addEventListener('contextmenu', closeContextMenu)
  await loadAll()
  nextTick(() => {
    initObserver()
  })
  await resumeSyncPollingIfRunning()
  loadRecentlyViewed()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('click', closeContextMenu)
  window.removeEventListener('contextmenu', closeContextMenu)
  stopSyncPolling()
  disposeStatus()
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
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.24);
  padding: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.rss-sync-status__text--active {
  color: hsl(var(--primary));
  font-weight: 650;
}

.rss-sync-menu {
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 50;
  width: 7rem;
  margin-top: 0.25rem;
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0.5rem;
  background: hsl(var(--popover));
  padding: 0.25rem;
  box-shadow: 0 8px 24px hsl(var(--foreground) / 0.12);
}

.rss-search-input {
  height: 2rem;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.36);
  padding: 0 0.75rem 0 2rem;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 500;
  outline: none;
  transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
}

.rss-search-input::placeholder {
  color: hsl(var(--muted-foreground) / 0.72);
}

.rss-search-input:hover {
  background: hsl(var(--muted) / 0.48);
}

.rss-search-input:focus {
  border-color: hsl(var(--primary) / 0.35);
  background: hsl(var(--background));
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.14);
}

.rss-entry-pane {
  width: 25rem;
}

.rss-entry-header {
  padding: 0.875rem;
}

.rss-back-button {
  display: flex;
  flex: none;
  align-items: center;
  gap: 0.25rem;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: 0.4375rem;
  background: hsl(var(--muted) / 0.36);
  padding: 0.25rem 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  font-weight: 700;
  outline: none;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.rss-back-button:hover {
  background: hsl(var(--muted) / 0.58);
  color: hsl(var(--foreground));
}

.rss-back-button:focus-visible,
.rss-filter-tab:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.35);
}

.rss-filter-tabs {
  display: flex;
  width: 100%;
}

.rss-filter-tab {
  flex: 1;
  font-size: 0.625rem;
  font-weight: 700;
}

.rss-entry-item {
  position: relative;
  display: flex;
  cursor: pointer;
  flex-direction: column;
  justify-content: space-between;
  padding: 1rem 0.875rem;
  outline: none;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.rss-entry-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.35);
}

.rss-sync-status__button {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--primary));
  font-weight: 650;
  transition:
    color 0.15s ease,
    opacity 0.15s ease;
}

.rss-sync-status__button:hover:not(:disabled) {
  color: hsl(var(--primary) / 0.82);
}

.rss-sync-status__button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
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

.rss-entry-item__category {
  display: inline-flex;
  align-items: center;
  font-size: 0.6875rem;
  font-weight: 700;
  transition: color 0.15s ease;
}

.rss-entry-item__date {
  color: hsl(var(--muted-foreground) / 0.6);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
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
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 2rem;
  height: 2rem;
  border: 1px solid hsl(var(--border) / 0.12);
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.3);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition:
    color 0.15s ease,
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.rss-browser-toolbar__button:hover {
  border-color: hsl(var(--border) / 0.28);
  background: hsl(var(--accent) / 0.5);
  color: hsl(var(--foreground));
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
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.28);
  padding: 0.25rem 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  font-weight: 600;
}

.rss-subscribe-dialog__body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
}

.rss-subscribe-dialog__field {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.rss-subscribe-dialog__field label {
  color: hsl(var(--foreground) / 0.82);
  font-size: 0.75rem;
  font-weight: 650;
}

.rss-subscribe-dialog__input-wrap {
  position: relative;
}

.rss-subscribe-dialog__input-icon {
  position: absolute;
  top: 50%;
  left: 0.75rem;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.55);
  transform: translateY(-50%);
  transition: color 0.15s ease;
  pointer-events: none;
}

.rss-subscribe-dialog__input-wrap:focus-within .rss-subscribe-dialog__input-icon {
  color: hsl(var(--foreground));
}

.rss-subscribe-dialog__input,
.rss-subscribe-dialog__category-button,
.rss-subscribe-dialog__custom-input {
  height: 2.25rem;
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.1);
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: none;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}

.rss-subscribe-dialog__input {
  padding-right: 0.875rem;
  padding-left: 2.25rem;
}

.rss-subscribe-dialog__input:hover,
.rss-subscribe-dialog__category-button:hover {
  background: hsl(var(--accent) / 0.15);
}

.rss-subscribe-dialog__input:focus-visible,
.rss-subscribe-dialog__custom-input:focus-visible {
  border-color: hsl(var(--primary) / 0.42);
  background: hsl(var(--background));
  outline: 1px solid hsl(var(--primary) / 0.2);
}

.rss-subscribe-dialog__category-button {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.75rem;
}

.rss-subscribe-dialog__category-menu {
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  z-index: 50;
  margin-top: 0.25rem;
  padding: 0.25rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.5rem;
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
}

.rss-subscribe-dialog__category-list {
  max-height: 12.5rem;
  padding-right: 0.25rem;
  overflow-y: auto;
}

.rss-subscribe-dialog__category-option,
.rss-subscribe-dialog__new-category {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}

.rss-subscribe-dialog__category-option {
  padding: 0 0.625rem;
  text-align: left;
}

.rss-subscribe-dialog__category-option:hover {
  background: hsl(var(--accent));
}

.rss-subscribe-dialog__empty {
  padding: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.62);
  font-size: 0.75rem;
  text-align: center;
}

.rss-subscribe-dialog__separator {
  height: 1px;
  margin: 0.25rem 0;
  background: hsl(var(--border) / 0.5);
}

.rss-subscribe-dialog__new-category {
  justify-content: center;
  padding: 0 0.625rem;
  color: hsl(var(--primary));
  font-weight: 650;
}

.rss-subscribe-dialog__new-category:hover {
  background: hsl(var(--primary) / 0.06);
}

.rss-subscribe-dialog__custom-input {
  padding-right: 2rem;
  padding-left: 0.625rem;
}

.rss-subscribe-dialog__confirm-category {
  position: absolute;
  top: 50%;
  right: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.375rem;
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  cursor: pointer;
  transform: translateY(-50%);
  transition: background-color 0.15s ease;
}

.rss-subscribe-dialog__confirm-category:hover {
  background: hsl(var(--primary) / 0.2);
}

.rss-subscribe-dialog__message {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.625rem;
  border: 1px solid;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.5;
}

.rss-subscribe-dialog__footer {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid hsl(var(--border) / 0.14);
  background: hsl(var(--muted) / 0.18);
}

.rss-subscribe-dialog__button {
  height: 2.25rem;
  padding: 0 0.75rem;
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    color 0.15s ease,
    background-color 0.15s ease,
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.rss-subscribe-dialog__button:hover {
  background: hsl(var(--accent) / 0.4);
}

.rss-subscribe-dialog__button--primary {
  padding-right: 1rem;
  padding-left: 1rem;
  border-color: hsl(var(--primary) / 0.42);
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
  border-radius: 0.625rem;
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

.rss-reader-empty-icon {
  display: flex;
  width: 5rem;
  height: 5rem;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: 0.875rem;
  background: hsl(var(--muted) / 0.28);
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
  text-align: justify;
  text-justify: normal;
  word-break: break-word;
  padding-top: 0.5rem;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.reader-content.font-sans {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
}

.reader-content.font-outfit {
  font-family: Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
}

.reader-content.font-serif {
  font-family: Georgia, Cambria, "Times New Roman", Times, "Nimbus Roman No9 L", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif !important;
}

.reader-content.font-lora {
  font-family: Lora, Georgia, Cambria, "Times New Roman", Times, "Nimbus Roman No9 L", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif !important;
}

/* Paragraphs — generous spacing, first-line indent for Chinese */
.reader-content :deep(p) {
  margin-bottom: 1.25rem;
  line-height: 2 !important;
  letter-spacing: 0.03em;
  color: hsl(var(--foreground) / 0.82);
  text-indent: 2em;
}

.reader-content :deep(p:first-child) {
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

.reader-content :deep(pre p) {
  text-indent: 0 !important;
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

.reader-content :deep(blockquote p) {
  text-indent: 0 !important;
  margin-bottom: 0.5rem !important;
  line-height: 2 !important;
}

.reader-content :deep(blockquote p:last-child) {
  margin-bottom: 0 !important;
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

  .rss-search-input,
  .rss-back-button,
  .rss-filter-tab,
  .rss-entry-item {
    transition: none;
  }
}
</style>
