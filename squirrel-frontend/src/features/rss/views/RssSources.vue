<template>
  <AppPageShell variant="compact" fill>
    <div class="flex h-full min-h-0 overflow-hidden bg-background text-foreground selection:bg-primary/10">
      <!-- 1. Left Sidebar: Accounts & Feeds -->
      <aside class="hidden min-h-0 w-[320px] shrink-0 flex-col border-r border-border/20 bg-muted/20 dark:bg-muted/5 lg:flex">
        <!-- Header -->
        <div class="flex h-20 shrink-0 items-center justify-between border-b border-border/20 px-5 bg-background/50 backdrop-blur-sm">
          <div class="min-w-0 flex flex-col justify-center">
            <h1 class="truncate text-lg font-bold tracking-tight text-foreground/90">RSS 内容源</h1>
            <p class="mt-0.5 text-xs font-medium text-muted-foreground/70">{{ accounts.length }} 个服务账号</p>
          </div>
          <Button 
            variant="ghost" 
            size="icon" 
            class="h-9 w-9 rounded-full bg-primary/5 hover:bg-primary/10 text-primary transition-colors shrink-0" 
            @click="openAddAccount"
          >
            <AppIcon name="plus" class="h-5 w-5" />
          </Button>
        </div>

        <!-- Controls: Dropdown & Search -->
        <div class="shrink-0 space-y-3 border-b border-border/10 p-4 bg-background/20 backdrop-blur-sm z-10">
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

          <!-- Selected Account Sync Info -->
          <div 
            v-if="selectedAccount" 
            class="flex items-center justify-between p-2 rounded-lg bg-accent/20 border border-border/10 text-xs text-muted-foreground/90"
          >
            <span 
              class="truncate pr-1 flex-1 min-w-0"
              :class="{ 'text-primary font-semibold animate-pulse': syncing, 'text-destructive': statusError }"
              :title="statusMessage"
            >
              {{ statusMessage || (selectedAccount.last_sync_at ? '同步于 ' + formatDate(selectedAccount.last_sync_at) : '从未同步') }}
            </span>
            <div class="relative flex items-center gap-0.5 shrink-0" ref="syncDropdownRef">
              <button 
                @click="syncSelectedAccount(false)" 
                class="flex items-center gap-1 font-semibold text-primary hover:text-primary/80 transition-all shrink-0" 
                :disabled="syncing"
              >
                <AppIcon name="refresh" class="h-3 w-3" :class="{ 'animate-spin': syncing }" />
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
                class="absolute right-0 top-full z-50 mt-1 w-28 rounded-lg border border-border/50 bg-background/95 backdrop-blur-xl p-1 shadow-lg"
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
              placeholder="搜索订阅源..." 
              class="h-8 w-full rounded-lg border border-transparent bg-accent/40 hover:bg-accent/60 pl-8 pr-3 text-xs font-medium outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/40 focus:bg-background"
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
      <section class="flex h-full min-h-0 w-full lg:w-[360px] xl:w-[400px] shrink-0 flex-col bg-background border-r border-border/10 relative z-10">
        <header class="relative flex shrink-0 flex-col border-b border-border/10 bg-background/70 p-4 backdrop-blur-2xl z-20">
          <div class="flex items-center justify-between w-full">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <button
                  v-if="feedNavStack"
                  @click="goBackFromFeed"
                  class="shrink-0 flex items-center gap-1 rounded-lg bg-accent/40 hover:bg-accent/60 px-2 py-1 text-[10px] font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  title="返回之前的列表"
                >
                  <AppIcon name="back" class="h-3 w-3" />
                  <span>返回</span>
                </button>
                <h2 class="truncate text-base font-bold tracking-tight text-foreground/90">
                  {{ selectedFeedTitle || selectedAccount?.name || 'RSS 阅读器' }}
                </h2>
              </div>
              <div class="mt-0.5 flex items-center gap-2 text-[10px] text-muted-foreground/80 font-medium">
                <span>{{ selectedFeedSubtitle }}</span>
                <div v-if="loading" class="flex items-center gap-1 ml-1">
                  <AppBounceDots />
                </div>
              </div>
            </div>
            
            <Button 
              variant="ghost" 
              size="icon" 
              class="h-7 w-7 rounded-lg bg-accent/40 hover:bg-accent/60 shrink-0" 
              @click="loadAll"
            >
              <AppIcon name="refresh" class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
            </Button>
          </div>

          <!-- Controls Toolbar Row -->
          <div class="flex flex-col gap-2 mt-3 w-full">
            <!-- Entry Search -->
            <div class="relative w-full group">
              <AppIcon name="search" class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary" />
              <input
                v-model="entrySearch"
                placeholder="搜索文章..."
                class="h-8 w-full rounded-lg border border-border/50 bg-accent/20 hover:bg-accent/40 pl-8 pr-3 text-xs outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/30 focus:bg-background"
              />
            </div>

            <!-- iOS/Reeder segmented control -->
            <div class="flex p-0.5 bg-muted/40 dark:bg-muted/10 rounded-lg border border-border/10">
              <button
                @click="activeFilter = 'all'"
                class="flex-1 py-1 text-[10px] font-bold rounded-md transition-all text-center cursor-pointer"
                :class="activeFilter === 'all' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
              >
                全部
              </button>
              <button
                @click="activeFilter = 'unread'"
                class="flex-1 py-1 text-[10px] font-bold rounded-md transition-all text-center cursor-pointer"
                :class="activeFilter === 'unread' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
              >
                未读
              </button>
              <button
                @click="activeFilter = 'starred'"
                class="flex-1 py-1 text-[10px] font-bold rounded-md transition-all text-center cursor-pointer"
                :class="activeFilter === 'starred' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
              >
                星标
              </button>
              <button
                @click="activeFilter = 'recent'"
                class="flex-1 py-1 text-[10px] font-bold rounded-md transition-all text-center cursor-pointer"
                :class="activeFilter === 'recent' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
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
              class="flex min-h-[20rem] flex-col items-center justify-center text-center py-10"
            >
              <AppSpinner size="lg" />
            </div>

            <!-- Empty view -->
            <div v-else-if="filteredEntries.length === 0" class="min-h-[20rem] py-10">
              <AppEmptyState
                variant="plain"
                icon="inbox"
                :title="activeFilter === 'recent' ? '暂无浏览记录' : '暂无相关文章'"
                :copy="activeFilter === 'recent' ? '浏览文章后，这里会记录您最近看过的内容。' : (selectedAccount ? '当前无对应文章，可点击同步获取最新内容。' : '请先添加并选择您的 RSS 账号。')"
              />
            </div>

            <!-- Articles List -->
            <div v-else class="flex flex-col divide-y divide-border/10 border-t border-b border-border/10">
              <div 
                v-for="entry in filteredEntries" 
                :key="entry.id"
                @click="openReader(entry)"
                @contextmenu.prevent.stop="showArticleContextMenu(entry, $event)"
                class="group relative flex flex-col justify-between py-4 px-3.5 transition-all duration-200 ease-out cursor-pointer animate-fade-in"
                :class="readingEntry && String(readingEntry.id) === String(entry.id) ? 'bg-primary/5' : 'bg-transparent hover:bg-accent/5'"
              >
                <!-- Card Top: Category & Time -->
                <div class="flex items-center justify-between text-xs text-muted-foreground/85 mb-2">
                  <span
                    class="inline-flex items-center text-[10px] font-bold tracking-wider uppercase transition-colors"
                    :class="entry.is_read ? 'text-muted-foreground/55' : 'text-primary'"
                  >
                    {{ getFeedCategory(entry.feed_id) }}
                  </span>
                  <div class="flex items-center gap-1.5">
                    <AppIcon v-if="entry.is_starred" name="star" class="h-3 w-3 text-amber-500 fill-amber-500" />
                    <span class="tabular-nums text-[10px] text-muted-foreground/60">{{ activeFilter === 'recent' ? formatRelativeTime((entry as RecentEntry).viewed_at) : formatDate(entry.published_at) }}</span>
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
                    class="text-[11px] leading-relaxed line-clamp-2 transition-colors"
                    :class="entry.is_read ? 'text-muted-foreground/50' : 'text-muted-foreground/70'"
                    v-html="stripHtmlTags(entry.summary)"
                  />
                </div>
                
                <!-- Card Bottom: Source & Media indicator (clickable to view feed) -->
                <div class="flex items-center pt-1">
                  <button
                    @click.stop="pushFeedNavStack(); selectFeed(entry.feed_id)"
                    class="flex items-center gap-2 min-w-0 text-left hover:text-primary transition-colors cursor-pointer"
                  >
                    <SiteIcon :icon-url="getFeedIconUrl(entry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
                    <span
                      class="text-[11px] font-semibold truncate transition-colors"
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
      <main class="hidden lg:flex h-full min-h-0 flex-1 min-w-0 flex-col bg-background relative overflow-hidden border-l border-border/10">
        <!-- If an article is selected, render it -->
        <div v-if="readingEntry" class="flex h-full min-h-0 flex-col overflow-hidden animate-fade-in bg-background relative">
          <!-- Reader Header (Clean compact toolbar) -->
          <header class="shrink-0 border-b border-border/10 h-14 px-6 bg-background flex items-center justify-between relative z-20">
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
            <div class="flex items-center gap-2 shrink-0">
              <!-- 应用内预览原文 -->
              <button 
                @click="openInAppBrowser"
                class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer"
                title="在应用内打开原文"
              >
                <AppIcon name="siteFallback" class="h-4 w-4" />
              </button>

              <!-- 在系统浏览器打开 -->
              <a 
                :href="readingEntry.canonical_url" 
                target="_blank" 
                rel="noopener noreferrer"
                class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5"
                title="在系统浏览器打开"
              >
                <AppIcon name="externalLink" class="h-4 w-4" />
              </a>

              <!-- 收藏 / 取消收藏 -->
              <button
                @click="toggleStarStatus(readingEntry)"
                class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer"
                :title="readingEntry.is_starred ? '取消收藏' : '收藏文章'"
              >
                <AppIcon name="star" class="h-4 w-4" :class="readingEntry.is_starred ? 'text-amber-500 fill-amber-500' : ''" />
              </button>

              <!-- 取消订阅该源 -->
              <button
                @click="unsubscribeCurrentFeedFromReader"
                class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-destructive/15 text-muted-foreground hover:text-destructive flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer"
                title="取消订阅该源"
              >
                <AppIcon name="close" class="h-4 w-4" />
              </button>

              <!-- Reader Settings -->
              <div class="relative" ref="readerSettingsRef">
                <button 
                  @click="showReaderSettings = !showReaderSettings"
                  class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer"
                  title="阅读个性化设置"
                >
                  <AppIcon name="settingsPanel" class="h-4 w-4" />
                </button>
                
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
            <div class="max-w-[42rem] mx-auto mb-8">
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
              class="reader-content prose prose-neutral dark:prose-invert max-w-[42rem] mx-auto text-foreground/80 py-2 space-y-0"
              :class="readerFontClass"
              :style="{ fontSize: readerFontSize + 'px' }"
              @click="handleContentClick"
              v-html="cleanAndDecodeHtml(readingEntry.summary) || '<p class=text-muted-foreground>该文章暂无正文内容。</p>'"
            />
          </div>

          <!-- Reeder-style Slide-over In-App Browser Overlay -->
          <div 
            v-if="showInAppBrowser"
            class="absolute inset-0 z-30 bg-background flex flex-col shadow-2xl border-l border-border/10 animate-fade-in"
          >
            <!-- Browser Toolbar -->
            <header class="shrink-0 border-b border-border/10 h-14 px-6 bg-background/95 backdrop-blur-md flex items-center justify-between relative z-20">
              <!-- Left Side: Back/Close button -->
              <div class="flex items-center gap-3 min-w-0">
                <button 
                  @click="showInAppBrowser = false"
                  class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer shrink-0"
                  title="返回正文"
                >
                  <AppIcon name="back" class="h-4 w-4" />
                </button>
                <div class="flex flex-col min-w-0 leading-tight">
                  <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">正在浏览原文</span>
                  <span class="text-xs font-semibold text-foreground/80 truncate max-w-[150px] lg:max-w-[280px]">
                    {{ readingEntry.title }}
                  </span>
                </div>
              </div>

              <!-- Center: Address Bar (Globe + Domain) -->
              <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 hidden md:flex items-center bg-accent/20 px-3 py-1 rounded-lg border border-border/5 text-[10px] font-medium text-muted-foreground/85 max-w-[220px] lg:max-w-[320px] truncate shadow-inner">
                <AppIcon name="siteFallback" class="h-3.5 w-3.5 mr-1.5 text-muted-foreground/60 shrink-0" />
                <span class="truncate">{{ getDisplayDomain(readingEntry.canonical_url) }}</span>
              </div>

              <!-- Right Side: Navigation & Refresh -->
              <div class="flex items-center gap-2 shrink-0">
                <!-- 刷新 -->
                <button 
                  @click="refreshIframe"
                  class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer"
                  title="重新加载"
                >
                  <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': iframeLoading }" />
                </button>

                <!-- 在系统浏览器打开 -->
                <a 
                  :href="readingEntry.canonical_url" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5"
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
              <div v-if="!isElectron && !iframeLoading" class="absolute bottom-4 right-4 max-w-xs p-3 rounded-xl border border-border bg-popover text-popover-foreground shadow-lg text-[10px] leading-relaxed z-20 flex flex-col gap-1.5 animate-fade-in">
                <span class="font-bold text-foreground">💡 原文加载提示</span>
                <span class="text-muted-foreground">如果页面显示空白或拒绝连接，是由于源站安全策略限制。您可以点击右上角图标在外部浏览器中打开。</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- If no article is selected, render a gorgeous premium workstation-themed placeholder -->
        <div v-else class="flex flex-col items-center justify-center flex-1 text-center p-8 bg-background/30 backdrop-blur-sm h-full select-none">
          <div class="h-20 w-20 rounded-2xl bg-accent/20 flex items-center justify-center mb-5 border border-border/10 shadow-inner ring-4 ring-accent/5 animate-pulse">
            <AppIcon name="library" class="h-9 w-9 text-primary/70" />
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
    <Dialog :open="showDeleteConfirmModal" @update:open="showDeleteConfirmModal = $event">
      <DialogContent class="max-w-sm overflow-hidden rounded-2xl p-0 border border-border/50 bg-background/95 backdrop-blur-xl">
        <DialogHeader class="border-b border-border/10 p-5 text-left">
          <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
            <AppIcon name="trash" class="h-5 w-5" />
          </div>
          <DialogTitle class="text-base font-semibold text-foreground">确认删除账号？</DialogTitle>
          <DialogDescription class="text-sm leading-relaxed text-muted-foreground/90 mt-1">
            此操作将永久移除该 RSS 账号「{{ accountToDelete?.name }}」及其同步的所有订阅源和文章记录。该操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2 bg-muted/30 p-4">
          <Button variant="outline" class="h-9 rounded-xl text-xs font-semibold" @click="showDeleteConfirmModal = false">取消</Button>
          <Button class="h-9 rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold" @click="handleDeleteAccount">确认删除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 5. Subscribe Feed Dialog -->
    <Dialog :open="showSubscribeModal" @update:open="showSubscribeModal = $event">
      <DialogContent class="max-w-md !overflow-visible rounded-xl p-0 border border-border/30 bg-background/95 backdrop-blur-xl shadow-xl transition-all duration-200">
        <DialogHeader class="border-b border-border/10 p-5 text-left">
          <DialogTitle class="text-base font-bold text-foreground">添加订阅源</DialogTitle>
          <DialogDescription class="text-xs text-muted-foreground mt-1 leading-normal">
            输入 RSS 订阅源 URL，将其添加到「{{ selectedAccount?.name }}」账号。
          </DialogDescription>
        </DialogHeader>

        <div class="p-5 space-y-4">
          <!-- Feed URL -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-foreground/80">订阅源 URL</label>
            <div class="relative group">
              <AppIcon name="link" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
              <Input
                v-model="subscribeForm.feedUrl"
                class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200"
                placeholder="https://example.com/rss/feed.xml"
              />
            </div>
          </div>

          <!-- Category (custom dropdown matching app style) -->
          <div class="space-y-1.5 relative" ref="categoryDropdownRef">
            <label class="text-xs font-semibold text-foreground/80">分类</label>
            <button
              @click="showCategoryDropdown = !showCategoryDropdown"
              class="flex h-9 w-full items-center justify-between rounded-lg border border-border/40 bg-accent/10 hover:bg-accent/15 px-3 text-xs font-medium transition-all"
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
              class="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-border/50 bg-popover text-popover-foreground p-1 shadow-lg ring-1 ring-black/5"
            >
              <div class="max-h-[200px] overflow-y-auto custom-scrollbar pr-1 space-y-0.5">
                <button
                  @click="subscribeForm.category = ''; showCategoryDropdown = false"
                  class="flex h-8 w-full items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent cursor-pointer"
                  :class="!subscribeForm.category ? 'text-foreground bg-accent/50 font-semibold' : 'text-muted-foreground'"
                >
                  <span>未分类</span>
                </button>
                <button
                  v-for="cat in existingCategories"
                  :key="cat"
                  @click="subscribeForm.category = cat; showCategoryDropdown = false"
                  class="flex h-8 w-full items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent cursor-pointer"
                  :class="subscribeForm.category === cat ? 'text-foreground bg-accent/50 font-semibold' : 'text-muted-foreground'"
                >
                  <span>{{ cat }}</span>
                </button>
                <div v-if="!existingCategories.length" class="py-3 text-center text-[10px] text-muted-foreground/60">暂无分类</div>
              </div>
              <div class="h-px w-full bg-border/50 my-1"></div>
              <div v-if="!showCustomCategoryInput" class="p-1">
                <button
                  @click="showCustomCategoryInput = true"
                  class="flex h-8 w-full items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold text-primary hover:bg-primary/5 transition-colors cursor-pointer"
                >
                  <AppIcon name="plus" class="h-3.5 w-3.5" />
                  新建分类
                </button>
              </div>
              <div v-else class="p-2">
                <div class="relative">
                  <Input
                    v-model="subscribeForm.customCategory"
                    class="h-8 rounded-lg pl-2.5 pr-8 border border-border/40 bg-accent/10 text-xs font-medium shadow-none"
                    placeholder="输入分类名称"
                    @keyup.enter="confirmCustomCategory"
                    ref="customCategoryInputRef"
                  />
                  <button
                    @click="confirmCustomCategory"
                    class="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 rounded-md bg-primary/10 hover:bg-primary/20 text-primary flex items-center justify-center transition-colors cursor-pointer"
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
              class="flex items-start gap-2 p-2.5 rounded-lg border text-xs leading-relaxed animate-fade-in"
              :class="subscribeError ? 'border-destructive/20 bg-destructive/5 text-destructive' : 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500'"
            >
              <AppIcon
                :name="subscribeError ? 'error' : 'check'"
                class="h-3.5 w-3.5 shrink-0 mt-0.5"
                :class="subscribeError ? 'text-destructive' : 'text-emerald-500'"
              />
              <span class="font-medium">{{ subscribeMessage }}</span>
            </div>
          </Transition>
        </div>

        <DialogFooter class="gap-2 bg-muted/20 dark:bg-muted/5 p-4 border-t border-border/10 flex flex-row items-center justify-end rounded-b-xl">
          <Button
            type="button"
            variant="outline"
            class="h-9 rounded-lg text-xs font-semibold px-3 border border-border/40 hover:bg-accent/40 transition-colors cursor-pointer"
            @click="closeSubscribeModal"
          >
            取消
          </Button>
          <Button
            type="button"
            class="h-9 rounded-lg text-xs font-semibold px-4 transition-all duration-150 cursor-pointer bg-foreground text-background hover:opacity-90 active:scale-[0.98]"
            :disabled="subscribingFeed || !subscribeForm.feedUrl.trim()"
            @click="handleSubscribeFeed"
          >
            <AppIcon v-if="subscribingFeed" name="refresh" class="h-3.5 w-3.5 mr-1.5 animate-spin" />
            添加订阅
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>



    <!-- Beautiful Full-screen Image Lightbox -->
    <div 
      v-if="activeLightboxImg" 
      class="fixed inset-0 z-[100] flex items-center justify-center bg-background/95 backdrop-blur-md transition-all duration-300 animate-fade-in"
      @click="closeLightbox"
    >
      <!-- Close Button -->
      <button 
        class="absolute top-5 right-5 h-10 w-10 rounded-full bg-accent/20 hover:bg-accent/40 text-foreground flex items-center justify-center backdrop-blur-md border border-border/10 transition-all cursor-pointer"
        @click.stop="closeLightbox"
      >
        <AppIcon name="close" class="h-5 w-5" />
      </button>
      
      <!-- Interactive Image -->
      <div class="relative max-w-[90vw] max-h-[90vh] overflow-hidden select-none">
        <img 
          :src="activeLightboxImg" 
          class="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl transition-transform duration-300 cursor-zoom-out"
          :style="{ transform: `scale(${lightboxScale})` }"
          @click.stop="closeLightbox"
        />
      </div>
    </div>

    <!-- Customized Right-Click Context Menu -->
    <RssArticleContextMenu
      :visible="showContextMenu"
      :entry="contextMenuEntry"
      :feed="contextMenuFeedResolved"
      :position="contextMenuPosition"
      :ref="bindContextMenuRef"
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
      :ref="bindFeedContextMenuRef"
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppBounceDots from '@/shared/components/AppBounceDots.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import ReaderSettingsPanel from '@/features/rss/components/ReaderSettingsPanel.vue'
import AccountDropdown from '@/features/rss/components/AccountDropdown.vue'
import FeedFolderTree from '@/features/rss/components/FeedFolderTree.vue'
import AccountEditDialog from '@/features/rss/components/AccountEditDialog.vue'
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
import RssFeedContextMenu from '@/features/rss/components/RssFeedContextMenu.vue'
import RssArticleContextMenu from '@/features/rss/components/RssArticleContextMenu.vue'
import type { RssEntry, RecentEntry, RssFeed } from '@/features/rss/composables/rssTypes'

// Cross-cutting UI state
const loading = ref(false)
const statusMessage = ref('')
const statusError = ref(false)

let statusTimeout: ReturnType<typeof setTimeout> | null = null

const onStatus = (message: string, isError = false) => {
  statusMessage.value = message
  statusError.value = isError
  if (statusTimeout) clearTimeout(statusTimeout)
  if (message && !message.includes('同步中')) {
    statusTimeout = setTimeout(() => {
      statusMessage.value = ''
      statusError.value = false
    }, 6000)
  }
}

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

// Cross-composable computed properties
const selectedFeedTitle = computed(() => {
  if (activeFilter.value === 'recent') return '最近浏览'
  if (selectedFeedId.value) {
    return feeds.value.find(f => f.id === selectedFeedId.value)?.title || '订阅源'
  }
  return null
})

const selectedFeedSubtitle = computed(() => {
  if (activeFilter.value === 'recent') return `共 ${recentlyViewed.value.length} 篇最近浏览的文章`
  if (selectedFeedId.value) {
    const feed = feeds.value.find(f => f.id === selectedFeedId.value)
    return `${feed?.category || '未分类'} · ${totalEntries.value} 篇文章`
  }
  if (selectedAccount.value) {
    return `共 ${totalEntries.value} 篇文章`
  }
  return '浏览您的 RSS 服务内容源'
})

// Orchestration functions
const closeContextMenu = () => {
  entriesCloseContextMenu()
  closeFeedContextMenu()
}

// ponytail: bridge the composable-owned feedContextMenuRef to the child
// component's exposed rootRef, so useRssFeeds can still measure the rendered
// menu for overflow repositioning after the template moved into the child.
type FeedContextMenuInstance = { rootRef?: HTMLElement | null }
const bindFeedContextMenuRef = (el: unknown) => {
  const instance = (el && typeof el === 'object' ? (el as FeedContextMenuInstance) : null)
  feedContextMenuRef.value = instance?.rootRef ?? null
}

// ponytail: same bridge for the article context menu; useRssEntries measures
// contextMenuRef for overflow repositioning.
const bindContextMenuRef = (el: unknown) => {
  const instance = (el && typeof el === 'object' ? (el as FeedContextMenuInstance) : null)
  contextMenuRef.value = instance?.rootRef ?? null
}

// ponytail: resolve the article menu's feed once here (the inline template
// called findFeedByEntry 4 times per render); pass it down as a prop.
const contextMenuFeedResolved = computed<RssFeed | null>(() =>
  contextMenuEntry.value ? (findFeedByEntry(contextMenuEntry.value) ?? null) : null,
)

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
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { 
  width: 5px; 
}
.custom-scrollbar::-webkit-scrollbar-track { 
  background: transparent; 
}
.custom-scrollbar::-webkit-scrollbar-thumb { 
  background: rgba(var(--primary), 0.1); 
  border-radius: 10px; 
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover { 
  background: rgba(var(--primary), 0.2); 
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
  border-left: 3px solid hsl(var(--primary) / 0.35);
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
</style>
