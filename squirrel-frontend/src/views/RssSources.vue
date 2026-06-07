<template>
  <AppPageShell variant="compact">
    <div class="flex h-full overflow-hidden bg-background text-foreground selection:bg-primary/10">
      <!-- 1. Left Sidebar: Accounts & Feeds -->
      <aside class="hidden w-[320px] shrink-0 flex-col border-r border-border/20 bg-muted/20 dark:bg-muted/5 lg:flex">
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
          <!-- Account Dropdown Selector -->
          <div class="relative w-full" ref="accountDropdownRef">
            <button
              @click="showAccountDropdown = !showAccountDropdown"
              class="flex h-8 w-full items-center justify-between rounded-lg border border-transparent bg-accent/40 hover:bg-accent/60 px-2.5 text-xs font-semibold transition-all"
              :class="selectedAccountId ? 'text-foreground border-primary/20 bg-primary/5' : 'text-muted-foreground'"
            >
              <div class="flex items-center gap-2 min-w-0">
                <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 text-primary" />
                <span class="truncate">{{ selectedAccount?.name || '选择账号...' }}</span>
              </div>
              <AppIcon 
                name="chevronDown" 
                class="h-3.5 w-3.5 transition-transform text-muted-foreground shrink-0" 
                :class="{ 'rotate-180': showAccountDropdown }" 
              />
            </button>
            
            <!-- Accounts Dropdown -->
            <div 
              v-if="showAccountDropdown" 
              class="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-border/50 bg-background/95 backdrop-blur-xl p-1 shadow-lg ring-1 ring-black/5"
            >
              <div class="max-h-[220px] overflow-y-auto custom-scrollbar pr-1 space-y-0.5">
                <div 
                  v-for="acc in accounts" 
                  :key="acc.id" 
                  @click="selectAccount(acc.id); showAccountDropdown = false" 
                  class="flex h-8 w-full items-center gap-2 rounded-lg px-2 text-left text-xs font-medium transition-colors hover:bg-accent cursor-pointer group/item" 
                  :class="selectedAccountId === acc.id ? 'text-foreground bg-accent/50 font-semibold' : 'text-muted-foreground'"
                >
                  <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 opacity-70" />
                  <span class="flex-1 truncate">
                    {{ acc.name }} 
                    <span class="text-[9px] text-muted-foreground/80 block">({{ acc.provider }})</span>
                  </span>
                  <!-- Action tools inside dropdown (pencil & delete) -->
                  <div class="flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity">
                    <button 
                      @click.stop="openEditAccount(acc); showAccountDropdown = false" 
                      class="h-7 w-7 rounded-md hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                      title="编辑账号"
                    >
                      <AppIcon name="pencil" class="h-3.5 w-3.5" />
                    </button>
                    <button 
                      @click.stop="confirmDeleteAccount(acc); showAccountDropdown = false" 
                      class="h-7 w-7 rounded-md hover:bg-destructive/15 flex items-center justify-center text-muted-foreground hover:text-destructive transition-colors"
                      title="删除账号"
                    >
                      <AppIcon name="trash" class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <div v-if="!accounts.length" class="py-4 text-center text-xs text-muted-foreground">暂无账号</div>
                <div class="h-px w-full bg-border/50 my-1"></div>
                <button 
                  @click="openAddAccount(); showAccountDropdown = false" 
                  class="flex h-9 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold text-primary hover:bg-primary/5 transition-colors"
                >
                  <AppIcon name="plus" class="h-4 w-4" />
                  添加服务账号
                </button>
              </div>
            </div>
          </div>

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

        <!-- Feeds Category Folding Tree -->
        <div class="flex-1 space-y-1 overflow-y-auto p-3 custom-scrollbar">
          <!-- All Feeds Item -->
          <div
            class="flex h-8 w-full items-center rounded-lg px-2.5 transition-all"
            :class="!selectedFeedId ? 'bg-transparent text-primary font-semibold' : 'text-muted-foreground'"
          >
            <button
              @click="selectedFeedId = null; loadEntries(true)"
              class="flex flex-1 items-center gap-3 text-left text-xs overflow-hidden h-full"
            >
              <AppIcon name="inbox" class="h-3.5 w-3.5 shrink-0" />
              <span class="truncate">全部订阅</span>
              <span class="text-xs opacity-60 ml-auto">{{ filteredFeeds.length }}</span>
            </button>
            <button
              v-if="selectedAccount"
              @click="showSubscribeModal = true"
              class="shrink-0 ml-1 rounded-md p-1 text-muted-foreground/50 hover:text-primary hover:bg-primary/10 transition-all"
              title="添加订阅源"
            >
              <AppIcon name="plus" class="h-3.5 w-3.5" />
            </button>
          </div>
          
          <div class="h-px bg-border/20 my-2"></div>
          
          <!-- Collapsible Folders -->
          <div v-for="folder in feedFolders" :key="folder.name" class="space-y-1">
            <!-- Folder Header -->
            <button 
              @click="toggleFolder(folder.name)" 
              class="flex w-full items-center justify-between px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              <div class="flex items-center gap-1.5 min-w-0">
                <AppIcon 
                  name="chevronRight" 
                  class="h-3 w-3 transition-transform text-muted-foreground/70 shrink-0" 
                  :class="{ 'rotate-90': collapsedFolders[folder.name] }" 
                />
                <span class="truncate">{{ folder.name }}</span>
              </div>
              <span class="text-[10px] bg-accent/60 px-1.5 py-0.5 rounded-full text-muted-foreground/80 shrink-0">{{ folder.feeds.length }}</span>
            </button>
            
            <!-- Folder Feeds List -->
            <div v-if="collapsedFolders[folder.name]" class="pl-3 space-y-0.5">
              <button
                v-for="feed in folder.feeds"
                :key="feed.id"
                @click="selectFeed(feed.id)"
                @contextmenu.prevent.stop="showFeedContextMenu(feed, $event)"
                class="group relative flex h-8 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-xs transition-all overflow-hidden"
                :class="selectedFeedId === feed.id ? 'bg-transparent text-primary font-semibold' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
              >
                <SiteIcon :icon-url="feed.icon_url || null" size="xs" rounded="sm" class="shrink-0" />
                <span class="flex-1 truncate">{{ feed.title }}</span>
                <button
                  @click.stop="handleUnsubscribeFeed(feed)"
                  class="shrink-0 rounded p-0.5 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all"
                  title="取消订阅"
                >
                  <AppIcon name="close" class="h-3 w-3" />
                </button>
              </button>
            </div>
          </div>

          <div v-if="!feedFolders.length" class="py-10 text-center text-xs text-muted-foreground">
            暂无匹配订阅源
          </div>
        </div>
      </aside>

      <!-- 2. Middle Column: Article List Flow -->
      <section class="flex h-full w-full lg:w-[360px] xl:w-[400px] shrink-0 flex-col bg-background border-r border-border/10 relative z-10">
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
                  <div class="h-1 w-1 animate-bounce rounded-full bg-primary/60 [animation-delay:-0.3s]" />
                  <div class="h-1 w-1 animate-bounce rounded-full bg-primary/80 [animation-delay:-0.15s]" />
                  <div class="h-1 w-1 animate-bounce rounded-full bg-primary" />
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
        <div ref="entriesContainer" class="flex-1 overflow-y-auto custom-scrollbar bg-background">
          <div class="w-full p-4 space-y-4">

            <div
              v-if="loading && filteredEntries.length === 0"
              class="flex min-h-[20rem] flex-col items-center justify-center text-center py-10"
            >
              <div class="h-7 w-7 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
            </div>

            <!-- Empty view -->
            <div
              v-else-if="filteredEntries.length === 0"
              class="flex min-h-[20rem] flex-col items-center justify-center text-center py-10"
            >
              <div class="h-16 w-16 rounded-full bg-accent/30 flex items-center justify-center mb-4 ring-4 ring-background shadow-inner">
                <AppIcon name="inbox" class="h-6 w-6 text-muted-foreground/45" />
              </div>
              <h3 class="text-sm font-bold tracking-tight text-foreground/80">{{ activeFilter === 'recent' ? '暂无浏览记录' : '暂无相关文章' }}</h3>
              <p class="mt-1 text-[11px] text-muted-foreground max-w-[200px] leading-relaxed">
                {{ activeFilter === 'recent' ? '浏览文章后，这里会记录您最近看过的内容。' : (selectedAccount ? '当前无对应文章，可点击同步获取最新内容。' : '请先添加并选择您的 RSS 账号。') }}
              </p>
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
              <div v-if="loadingMoreEntries" class="h-6 w-6 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Right Column: Permanent Article Content Reader -->
      <main class="hidden lg:flex flex-1 min-w-0 flex-col bg-background relative h-full overflow-hidden border-l border-border/10">
        <!-- If an article is selected, render it -->
        <div v-if="readingEntry" class="flex flex-col h-full overflow-hidden animate-fade-in bg-background relative">
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

              <!-- 阅读设置 -->
              <div class="relative" ref="readerSettingsRef">
                <button 
                  @click="showReaderSettings = !showReaderSettings"
                  class="h-8 w-8 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/5 cursor-pointer"
                  title="阅读个性化设置"
                >
                  <AppIcon name="settingsPanel" class="h-4 w-4" />
                </button>
                
                <!-- Preference dropdown (opens to left) -->
                <div 
                  v-if="showReaderSettings" 
                  class="absolute right-0 top-full z-50 mt-1.5 w-48 rounded-xl border border-border/30 bg-popover text-popover-foreground p-3 shadow-[0_4px_16px_rgba(0,0,0,0.04)] dark:shadow-[0_4px_24px_rgba(0,0,0,0.4)] space-y-3 animate-fade-in"
                >
                  <!-- Font Family toggle -->
                  <div class="space-y-1">
                    <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block">排版字体</span>
                    <div class="grid grid-cols-2 gap-1 bg-accent/20 p-0.5 rounded-lg border border-border/5">
                      <button 
                        @click="readerFontFamily = 'sans'; saveReaderPrefs()"
                        class="py-1 text-[10px] font-semibold rounded-md transition-all text-center cursor-pointer"
                        :class="readerFontFamily === 'sans' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                        title="极简现代 (Inter)"
                      >
                        Inter
                      </button>
                      <button 
                        @click="readerFontFamily = 'outfit'; saveReaderPrefs()"
                        class="py-1 text-[10px] font-semibold rounded-md transition-all text-center cursor-pointer"
                        :class="readerFontFamily === 'outfit' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                        title="优雅圆润 (Outfit)"
                      >
                        Outfit
                      </button>
                      <button 
                        @click="readerFontFamily = 'serif'; saveReaderPrefs()"
                        class="py-1 text-[10px] font-semibold rounded-md transition-all text-center font-serif cursor-pointer"
                        :class="readerFontFamily === 'serif' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                        title="经典衬线 (Georgia)"
                      >
                        Georgia
                      </button>
                      <button 
                        @click="readerFontFamily = 'lora'; saveReaderPrefs()"
                        class="py-1 text-[10px] font-semibold rounded-md transition-all text-center font-serif cursor-pointer"
                        :class="readerFontFamily === 'lora' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                        title="人文阅读 (Lora)"
                      >
                        Lora
                      </button>
                    </div>
                  </div>
                  
                  <!-- Font Size toggle -->
                  <div class="space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block">字号大小</span>
                      <span class="text-[10px] font-semibold tabular-nums text-foreground/80">{{ readerFontSize }}px</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <button 
                        @click="setReaderFontSize(readerFontSize - 1)" 
                        class="h-7 w-7 rounded-lg border border-border/50 bg-accent/25 hover:bg-accent/40 flex items-center justify-center text-xs font-bold transition-all text-muted-foreground hover:text-foreground cursor-pointer flex-1"
                        :disabled="readerFontSize <= 12"
                      >
                        A-
                      </button>
                      <button 
                        @click="setReaderFontSize(readerFontSize + 1)" 
                        class="h-7 w-7 rounded-lg border border-border/50 bg-accent/25 hover:bg-accent/40 flex items-center justify-center text-xs font-bold transition-all text-muted-foreground hover:text-foreground cursor-pointer flex-1"
                        :disabled="readerFontSize >= 24"
                      >
                        A+
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </header>
          
          <!-- Reader Body Scroll Container -->
          <div 
            ref="readerScrollContainer"
            class="flex-1 overflow-y-auto custom-scrollbar px-5 md:px-16 lg:px-28 py-8 bg-background relative"
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
            <div class="flex-1 w-full h-full overflow-hidden bg-background relative flex flex-col">
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
    <Dialog :open="showAddEditModal" @update:open="showAddEditModal = $event">
      <DialogContent class="max-w-md overflow-hidden rounded-xl p-0 border border-border/30 bg-background/95 backdrop-blur-xl shadow-xl transition-all duration-200">
        <DialogHeader class="border-b border-border/10 p-5 text-left">
          <DialogTitle class="text-base font-bold text-foreground">
            {{ accountForm.id ? '编辑 RSS 账号' : '添加 RSS 账号' }}
          </DialogTitle>
          <DialogDescription class="text-xs text-muted-foreground mt-1 leading-normal">
            连接第三方 RSS 服务账号，支持 Google Reader API, Miniflux, Fever 等规范。
          </DialogDescription>
        </DialogHeader>
        
        <div class="p-5 space-y-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
          <!-- Provider Select (Segmented Switcher) -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-foreground/80">服务提供商</label>
            <div class="flex p-0.5 bg-muted/40 dark:bg-muted/10 rounded-lg border border-border/10">
              <button
                v-for="prov in providers"
                :key="prov.value"
                type="button"
                @click="accountForm.provider = prov.value"
                class="flex-1 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 text-center cursor-pointer flex items-center justify-center gap-1.5 select-none"
                :class="accountForm.provider === prov.value
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'"
              >
                <AppIcon :name="prov.icon" class="h-3.5 w-3.5 shrink-0" />
                <span>{{ prov.name }}</span>
              </button>
            </div>
          </div>
          
          <!-- Account Name -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-foreground/80">账号名称</label>
            <div class="relative group">
              <AppIcon name="pencil" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
              <Input 
                v-model="accountForm.name" 
                class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200" 
                placeholder="例如: 我的 Miniflux" 
              />
            </div>
          </div>
          
          <!-- Base URL -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-foreground/80">服务接口地址 (URL)</label>
            <div class="relative group">
              <AppIcon name="link" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
              <Input 
                v-model="accountForm.base_url" 
                class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200" 
                :placeholder="baseUrlPlaceholder" 
              />
            </div>
          </div>
          
          <!-- Username -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="text-xs font-semibold text-foreground/80">用户名</label>
              <span 
                v-if="accountForm.provider === 'greader' || accountForm.provider === 'fever'"
                class="text-[10px] text-destructive/80 font-bold animate-fade-in"
              >
                * 必填
              </span>
            </div>
            <div class="relative group">
              <AppIcon name="user" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
              <Input 
                v-model="accountForm.username" 
                class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200" 
                placeholder="用户名 (Google Reader 与 Fever 需要)" 
              />
            </div>
          </div>
          
          <!-- Credential -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="text-xs font-semibold text-foreground/80">{{ credentialPlaceholder }}</label>
              <span 
                v-if="!accountForm.id"
                class="text-[10px] text-destructive/80 font-bold animate-fade-in"
              >
                * 必填
              </span>
            </div>
            <div class="relative group">
              <AppIcon name="security" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
              <Input 
                v-model="accountForm.credential" 
                type="password"
                class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200" 
                :placeholder="accountForm.id ? '留空表示不修改密码或 Token' : '密码或 API Token'" 
              />
            </div>
          </div>
          
          <div class="h-px bg-border/10 my-2"></div>
          
          <!-- Enabled Switch -->
          <div class="flex items-center justify-between py-1.5 select-none">
            <div class="flex flex-col text-left pr-4">
              <span class="text-xs font-semibold text-foreground/90">启用此账号同步</span>
              <span class="text-[10px] text-muted-foreground/60 mt-0.5 leading-normal">开启后系统将自动定期在后台同步此账号的订阅内容</span>
            </div>
            <button
              type="button"
              @click="accountForm.enabled = !accountForm.enabled"
              class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
              :class="accountForm.enabled ? 'bg-foreground' : 'bg-muted/80'"
            >
              <span
                class="pointer-events-none inline-block h-4 w-4 transform rounded-full bg-background shadow-sm transition duration-200 ease-in-out"
                :class="accountForm.enabled ? 'translate-x-4' : 'translate-x-0'"
              />
            </button>
          </div>
          
          <!-- Error / Success Message -->
          <Transition name="fade">
            <div 
              v-if="formMessage" 
              class="flex items-start gap-2 p-2.5 rounded-lg border text-xs leading-relaxed animate-fade-in"
              :class="formError ? 'border-destructive/20 bg-destructive/5 text-destructive' : 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500'"
            >
              <AppIcon 
                :name="formError ? 'error' : 'check'" 
                class="h-3.5 w-3.5 shrink-0 mt-0.5" 
                :class="formError ? 'text-destructive' : 'text-emerald-500'" 
              />
              <span class="font-medium">{{ formMessage }}</span>
            </div>
          </Transition>
        </div>
        
        <DialogFooter class="gap-2 bg-muted/20 dark:bg-muted/5 p-4 border-t border-border/10 flex flex-row items-center justify-between">
          <Button 
            type="button" 
            variant="outline" 
            class="h-9 rounded-lg text-xs font-semibold px-3 border border-border/40 hover:bg-accent/40 transition-colors cursor-pointer shrink-0" 
            :disabled="testing || !canTestForm" 
            @click="testForm"
          >
            <AppIcon v-if="testing" name="refresh" class="h-3.5 w-3.5 mr-1.5 animate-spin text-foreground" />
            <AppIcon v-else name="sync" class="h-3.5 w-3.5 mr-1.5 opacity-70" />
            测试连接
          </Button>
          <div class="flex gap-2 justify-end">
            <Button 
              type="button" 
              variant="outline" 
              class="h-9 rounded-lg text-xs font-semibold px-3 border border-border/40 hover:bg-accent/40 transition-colors cursor-pointer" 
              @click="showAddEditModal = false"
            >
              取消
            </Button>
            <Button 
              type="button"
              class="h-9 rounded-lg text-xs font-semibold px-4 transition-all duration-150 cursor-pointer bg-foreground text-background hover:opacity-90 active:scale-[0.98]" 
              :disabled="saving || !canSaveForm" 
              @click="saveAccount"
            >
              <AppIcon v-if="saving" name="refresh" class="h-3.5 w-3.5 mr-1.5 animate-spin" />
              {{ accountForm.id ? '保存修改' : '确认添加' }}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>

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

    <!-- 6. Premium Slide-over Reader View Drawer (Mobile Fallback) -->
    <Sheet :open="isMobile && !!readingEntry" @update:open="closeReader">
      <SheetContent class="w-full sm:max-w-[640px] md:max-w-[768px] lg:max-w-[900px] border-l border-border/20 bg-background/95 backdrop-blur-xl p-0 flex flex-col h-full shadow-2xl">
        <div v-if="readingEntry" class="flex flex-col h-full overflow-hidden">
          <!-- Reader Header -->
          <header class="shrink-0 border-b border-border/10 p-5 bg-background/50 backdrop-blur-sm pr-16 flex flex-col gap-3 relative z-20">
            <!-- Top Metadata & Controls Row -->
            <div class="flex items-center justify-between">
              <!-- Metadata (Feed Source & Date) -->
              <div class="flex items-center gap-2 text-xs text-muted-foreground/80">
                <span class="px-2 py-0.5 rounded bg-primary/10 text-primary font-bold uppercase tracking-wider text-[9px]">
                  {{ getFeedCategory(readingEntry.feed_id) }}
                </span>
                <span>•</span>
                <span class="font-bold text-foreground/80">{{ getFeedTitle(readingEntry.feed_id) }}</span>
                <span>•</span>
                <span class="tabular-nums text-muted-foreground/60 text-[11px]">{{ formatDate(readingEntry.published_at) }}</span>
              </div>
              
              <!-- Clean Flat Action Buttons -->
              <div class="flex items-center gap-1.5 pr-2">
                <!-- 访问原始网页 -->
                <a 
                  :href="readingEntry.canonical_url" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="h-7 w-7 rounded-lg bg-accent/40 hover:bg-accent/60 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all"
                  title="访问原始网页"
                >
                  <AppIcon name="externalLink" class="h-4 w-4" />
                </a>

                <!-- Mobile Reading Preferences Menu -->
                <div class="relative" ref="mobileReaderSettingsRef">
                  <button 
                    @click="showMobileReaderSettings = !showMobileReaderSettings"
                    class="h-7 w-7 rounded-lg bg-accent/30 hover:bg-accent/50 text-muted-foreground hover:text-foreground flex items-center justify-center transition-all cursor-pointer"
                    title="阅读设置"
                  >
                    <AppIcon name="settingsPanel" class="h-4 w-4" />
                  </button>
                  
                  <div 
                    v-if="showMobileReaderSettings" 
                    class="absolute right-0 top-full z-50 mt-1.5 w-48 rounded-xl border border-border/30 bg-popover text-popover-foreground p-3 shadow-[0_4px_16px_rgba(0,0,0,0.04)] dark:shadow-[0_4px_24px_rgba(0,0,0,0.4)] space-y-3 animate-fade-in"
                  >
                    <!-- Font Family toggle -->
                    <div class="space-y-1">
                      <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block">排版字体</span>
                      <div class="grid grid-cols-2 gap-1 bg-accent/20 p-0.5 rounded-lg border border-border/5">
                        <button 
                          @click="readerFontFamily = 'sans'; saveReaderPrefs()"
                          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center cursor-pointer"
                          :class="readerFontFamily === 'sans' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                          title="极简现代 (Inter)"
                        >
                          Inter
                        </button>
                        <button 
                          @click="readerFontFamily = 'outfit'; saveReaderPrefs()"
                          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center cursor-pointer"
                          :class="readerFontFamily === 'outfit' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                          title="优雅圆润 (Outfit)"
                        >
                          Outfit
                        </button>
                        <button 
                          @click="readerFontFamily = 'serif'; saveReaderPrefs()"
                          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center font-serif cursor-pointer"
                          :class="readerFontFamily === 'serif' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                          title="经典衬线 (Georgia)"
                        >
                          Georgia
                        </button>
                        <button 
                          @click="readerFontFamily = 'lora'; saveReaderPrefs()"
                          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center font-serif cursor-pointer"
                          :class="readerFontFamily === 'lora' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                          title="人文阅读 (Lora)"
                        >
                          Lora
                        </button>
                      </div>
                    </div>
                    
                    <!-- Font Size toggle -->
                    <div class="space-y-1">
                      <div class="flex items-center justify-between">
                        <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block">字号大小</span>
                        <span class="text-[10px] font-semibold tabular-nums text-foreground/80">{{ readerFontSize }}px</span>
                      </div>
                      <div class="flex items-center gap-1">
                        <button 
                          @click="setReaderFontSize(readerFontSize - 1)" 
                          class="h-7 w-7 rounded-lg border border-border/50 bg-accent/25 hover:bg-accent/40 flex items-center justify-center text-xs font-bold transition-all text-muted-foreground hover:text-foreground cursor-pointer flex-1"
                          :disabled="readerFontSize <= 12"
                        >
                          A-
                        </button>
                        <button 
                          @click="setReaderFontSize(readerFontSize + 1)" 
                          class="h-7 w-7 rounded-lg border border-border/50 bg-accent/25 hover:bg-accent/40 flex items-center justify-center text-xs font-bold transition-all text-muted-foreground hover:text-foreground cursor-pointer flex-1"
                          :disabled="readerFontSize >= 24"
                        >
                          A+
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Title -->
            <h3 class="text-base md:text-lg font-bold tracking-tight text-foreground leading-snug">
              {{ readingEntry.title }}
            </h3>
          </header>
          
          <!-- Reader Body Scroll Container -->
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
            <!-- Description / HTML content -->
            <div 
              class="reader-content prose prose-sm dark:prose-invert max-w-none text-foreground/80 py-2 space-y-0"
              :class="readerFontClass"
              :style="{ fontSize: readerFontSize + 'px' }"
              @click="handleContentClick"
              v-html="cleanAndDecodeHtml(readingEntry.summary) || '<p class=text-muted-foreground>该文章暂无正文内容。</p>'"
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>

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
    <Teleport to="body">
      <div
        v-if="showContextMenu && contextMenuEntry"
        ref="contextMenuRef"
        class="fixed z-[9999] w-[200px] rounded-xl border border-border/30 bg-popover/90 backdrop-blur-xl p-1.5 shadow-[0_6px_20px_rgba(0,0,0,0.06)] dark:shadow-[0_10px_30px_rgba(0,0,0,0.18)] animate-fade-in"
        :style="{ left: contextMenuPosition.x + 'px', top: contextMenuPosition.y + 'px' }"
      >
        <div class="flex flex-col gap-0.5">
          <button
            @click="toggleReadStatus(contextMenuEntry)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon :name="contextMenuEntry.is_read ? 'eyeOff' : 'eye'" class="h-3.5 w-3.5 opacity-70" />
            <span>{{ contextMenuEntry.is_read ? '标记为未读' : '标记为已读' }}</span>
          </button>

          <button
            @click="toggleStarStatus(contextMenuEntry)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="star" class="h-3.5 w-3.5 opacity-70" :class="contextMenuEntry.is_starred ? 'text-amber-500 fill-amber-500' : ''" />
            <span>{{ contextMenuEntry.is_starred ? '取消收藏' : '收藏文章' }}</span>
          </button>

          <button
            @click="goToFeedFromContextMenu(contextMenuEntry)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="inbox" class="h-3.5 w-3.5 opacity-70" />
            <span>查看订阅源</span>
          </button>

          <div class="h-px bg-border/20 my-1"></div>

          <template v-if="findFeedByEntry(contextMenuEntry)">
            <div class="px-2.5 py-1 text-[9px] font-bold text-muted-foreground uppercase tracking-wider">默认打开方式</div>

            <button
              @click="setFeedOpenMethod(findFeedByEntry(contextMenuEntry)!, null)"
              class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
            >
              <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
              <span class="flex-1">内嵌阅读</span>
              <AppIcon v-if="!findFeedByEntry(contextMenuEntry)!.open_method" name="check" class="h-3 w-3 text-primary" />
            </button>

            <button
              @click="setFeedOpenMethod(findFeedByEntry(contextMenuEntry)!, 'app_browser')"
              class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
            >
              <AppIcon name="siteFallback" class="h-3.5 w-3.5 opacity-70" />
              <span class="flex-1">应用内浏览器</span>
              <AppIcon v-if="findFeedByEntry(contextMenuEntry)!.open_method === 'app_browser'" name="check" class="h-3 w-3 text-primary" />
            </button>

            <button
              @click="setFeedOpenMethod(findFeedByEntry(contextMenuEntry)!, 'external_browser')"
              class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
            >
              <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
              <span class="flex-1">系统浏览器</span>
              <AppIcon v-if="findFeedByEntry(contextMenuEntry)!.open_method === 'external_browser'" name="check" class="h-3 w-3 text-primary" />
            </button>
          </template>

          <button
            @click="batchUpdateReadStatus('above', true)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
            <span>上方全部已读</span>
          </button>

          <button
            @click="batchUpdateReadStatus('below', true)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
            <span>下方全部已读</span>
          </button>

          <button
            @click="batchUpdateReadStatus('all', true)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
            <span>列表全部已读</span>
          </button>

          <button
            @click="batchUpdateReadStatus('all', false)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="eyeOff" class="h-3.5 w-3.5 opacity-70" />
            <span>列表全部未读</span>
          </button>

          <div class="h-px bg-border/20 my-1"></div>

          <button
            @click="unsubscribeCurrentFeed(contextMenuEntry)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-destructive cursor-pointer"
          >
            <AppIcon name="close" class="h-3.5 w-3.5 opacity-70" />
            <span>取消订阅该源</span>
          </button>

          <div class="h-px bg-border/20 my-1"></div>

          <button
            @click="copyArticleLink(contextMenuEntry)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="link" class="h-3.5 w-3.5 opacity-70" />
            <span>复制文章链接</span>
          </button>

          <button
            @click="openInExternalBrowser(contextMenuEntry)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
            <span>在外部浏览器打开</span>
          </button>
        </div>
      </div>
    </Teleport>

    <!-- Customized Feed Right-Click Context Menu -->
    <Teleport to="body">
      <div
        v-if="showFeedContextMenuState && contextMenuFeed"
        ref="feedContextMenuRef"
        class="fixed z-[9999] w-[200px] rounded-xl border border-border/30 bg-popover/90 backdrop-blur-xl p-1.5 shadow-[0_6px_20px_rgba(0,0,0,0.06)] dark:shadow-[0_10px_30px_rgba(0,0,0,0.18)] animate-fade-in"
        :style="{ left: feedContextMenuPosition.x + 'px', top: feedContextMenuPosition.y + 'px' }"
      >
        <div class="flex flex-col gap-0.5">
          <button
            @click="markFeedAllAsRead(contextMenuFeed)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
            <span>全部标记为已读</span>
          </button>

          <button
            @click="syncFeedFromContextMenu(contextMenuFeed)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="refresh" class="h-3.5 w-3.5 opacity-70" />
            <span>同步文章</span>
          </button>

          <button
            @click="copyFeedLink(contextMenuFeed)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="link" class="h-3.5 w-3.5 opacity-70" />
            <span>复制订阅源地址</span>
          </button>

          <button
            v-if="contextMenuFeed.site_url"
            @click="openFeedSiteInExternalBrowser(contextMenuFeed)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
            <span>访问源网站</span>
          </button>

          <div class="h-px bg-border/20 my-1"></div>

          <div class="px-2.5 py-1 text-[9px] font-bold text-muted-foreground uppercase tracking-wider">默认打开方式</div>

          <button
            @click="setFeedOpenMethod(contextMenuFeed!, null)"
            class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">内嵌阅读</span>
            <AppIcon v-if="!contextMenuFeed.open_method" name="check" class="h-3 w-3 text-primary" />
          </button>

          <button
            @click="setFeedOpenMethod(contextMenuFeed!, 'app_browser')"
            class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="siteFallback" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">应用内浏览器</span>
            <AppIcon v-if="contextMenuFeed.open_method === 'app_browser'" name="check" class="h-3 w-3 text-primary" />
          </button>

          <button
            @click="setFeedOpenMethod(contextMenuFeed!, 'external_browser')"
            class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">系统浏览器</span>
            <AppIcon v-if="contextMenuFeed.open_method === 'external_browser'" name="check" class="h-3 w-3 text-primary" />
          </button>

          <div class="h-px bg-border/20 my-1"></div>

          <button
            @click="unsubscribeFeedFromContextMenu(contextMenuFeed)"
            class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-destructive cursor-pointer"
          >
            <AppIcon name="close" class="h-3.5 w-3.5 opacity-70" />
            <span>取消订阅</span>
          </button>
        </div>
      </div>
    </Teleport>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { onClickOutside } from '@vueuse/core'
import {
  getRssSyncStatus,
  syncRssAccount,
} from '@/api'
import AppIcon from '@/components/common/AppIcon.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { formatDate } from '../utils/dateFormat'
import { useRssAccounts } from '@/composables/useRssAccounts'
import { useRssFeeds } from '@/composables/useRssFeeds'
import { useRssEntries } from '@/composables/useRssEntries'
import { useRssReader } from '@/composables/useRssReader'
import type { RssEntry, RecentEntry } from '@/composables/rssTypes'
import type { ApiResult } from '@/composables/rssTypes'

// Cross-cutting UI state
const loading = ref(false)
const statusMessage = ref('')
const statusError = ref(false)

let statusTimeout: ReturnType<typeof setTimeout> | null = null

const setStatus = (message: string, isError = false) => {
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

// Sync state
const syncing = ref(false)
const showSyncMenu = ref(false)
const syncDropdownRef = ref<HTMLElement | null>(null)
let syncPollTimer: ReturnType<typeof setInterval> | null = null

const getRssSyncModeLabel = (syncMode?: string) => {
  return syncMode === 'full' ? '全量同步' : '轻量同步'
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
  accountDropdownRef,
  saving,
  testing,
  accountForm,
  formMessage,
  formError,
  selectedAccount,
  defaultAccountName,
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
  onStatus: setStatus,
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
  onStatus: setStatus,
})

const {
  readingEntry,
  readerScrollContainer,
  readerFontSize,
  readerFontFamily,
  showReaderSettings,
  readerSettingsRef,
  showMobileReaderSettings,
  mobileReaderSettingsRef,
  showInAppBrowser,
  iframeLoading,
  iframeLoadKey,
  iframeProgress,
  isElectron,
  iframeRef,
  activeLightboxImg,
  lightboxScale,
  isMobile,
  readerFontClass,
  setReaderFontSize,
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
  closeReader,
  openRecentEntry,
  unsubscribeCurrentFeedFromReader,
  checkIfMobile,
} = useRssReader({
  selectedAccountId,
  feeds,
  findFeedByEntry,
  getFeedTitle,
  getFeedCategory,
  getFeedIconUrl,
  onStatus: setStatus,
  onRefreshFeeds: loadFeeds,
  onRefreshEntries: (isReset) => loadEntries(isReset ?? true),
})

const {
  entries,
  activeFilter,
  entrySearch,
  page,
  pageSize,
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
  hasMoreEntries,
  filteredEntries,
  loadEntries,
  loadMore,
  loadRecentlyViewed,
  recordRecentlyViewed,
  resetScroll,
  pushFeedNavStack,
  goBackFromFeed,
  toggleReadStatus,
  getBatchReadTargets,
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
  onStatus: setStatus,
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
    setStatus('未找到对应的订阅源', true)
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

// Sync polling
const pollSyncProgress = () => {
  if (syncPollTimer) clearInterval(syncPollTimer)
  const accountId = selectedAccountId.value
  if (!accountId) {
    syncing.value = false
    return
  }

  syncPollTimer = setInterval(async () => {
    const result = await getRssSyncStatus(accountId) as ApiResult<any>
    if (result.error) {
      clearInterval(syncPollTimer!)
      syncPollTimer = null
      syncing.value = false
      setStatus(result.error.message || '获取同步状态失败', true)
      return
    }
    const data = result.data
    if (!data) return
    const modeLabel = getRssSyncModeLabel(data.sync_mode)
    if (data.running) {
      const phaseLabel: Record<string, string> = {
        starting: '启动中',
        feeds_fetching: '同步订阅源',
        feeds_saving: '同步订阅源',
        entries_fetching: '同步文章',
        entries_saving: '同步文章',
      }
      const label = phaseLabel[data.phase] || data.phase
      let progress = ''
      if (data.phase === 'entries_fetching') {
        progress = data.entries_fetched != null ? `已获取 ${data.entries_fetched} 篇` : '等待服务器响应...'
      } else if (data.phase === 'entries_saving') {
        progress = `已更新 ${data.entries_synced || 0} 篇`
      } else if (data.feeds_synced != null) {
        progress = `${data.feeds_synced} 个`
      }
      setStatus(`${modeLabel}中 [${label}] ${progress}`, false)
    } else {
      clearInterval(syncPollTimer!)
      syncPollTimer = null
      syncing.value = false
      if (data.phase === 'completed') {
        const changedEntries = data.entries_synced || 0
        const entryText = changedEntries > 0 ? `已更新 ${changedEntries} 篇文章` : '所有内容已是最新'
        setStatus(`${modeLabel}完成：${entryText}`)
      } else {
        setStatus(data.message || data.error || '同步失败', true)
      }
      await loadAccounts()
      await loadFeeds()
      await loadEntries(true)
    }
  }, 1000)
}

const syncSelectedAccount = async (forceFullSync = false) => {
  if (!selectedAccountId.value) return
  syncing.value = true
  statusMessage.value = ''
  const result = await syncRssAccount(selectedAccountId.value, undefined, forceFullSync)
  if (result.error) {
    syncing.value = false
    setStatus(result.error.message || '启动同步失败', true)
    return
  }
  pollSyncProgress()
}

const resumeSyncPollingIfRunning = async () => {
  const accountId = selectedAccountId.value
  if (!accountId) return
  const result = await getRssSyncStatus(accountId) as ApiResult<any>
  if (result.error) return
  const data = result.data
  if (data && data.running) {
    syncing.value = true
    pollSyncProgress()
  }
}

// Click outside handlers (for component-level refs)
onClickOutside(syncDropdownRef, () => {
  showSyncMenu.value = false
})

// Watchers
watch(selectedAccountId, () => {
  collapsedFolders.value = {}
})

// Lifecycle
onMounted(async () => {
  checkIfMobile()
  window.addEventListener('resize', checkIfMobile)
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
  window.removeEventListener('resize', checkIfMobile)
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('click', closeContextMenu)
  window.removeEventListener('contextmenu', closeContextMenu)
  if (syncPollTimer) {
    clearInterval(syncPollTimer)
    syncPollTimer = null
  }
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
