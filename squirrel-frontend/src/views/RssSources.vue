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
                <span>增量</span>
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
          <button
            @click="selectedFeedId = null; loadEntries(true)"
            class="group relative flex h-8 w-full items-center gap-3 rounded-lg px-2.5 text-left text-xs transition-all overflow-hidden"
            :class="!selectedFeedId ? 'bg-primary/5 text-primary font-semibold' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground font-medium'"
          >
            <AppIcon name="inbox" class="h-3.5 w-3.5 shrink-0" />
            <span class="flex-1 truncate">全部文章</span>
            <span class="text-xs opacity-60">{{ filteredFeeds.length }}</span>
          </button>
          
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
                  :class="{ 'rotate-90': !collapsedFolders[folder.name] }" 
                />
                <span class="truncate">{{ folder.name }}</span>
              </div>
              <span class="text-[10px] bg-accent/60 px-1.5 py-0.5 rounded-full text-muted-foreground/80 shrink-0">{{ folder.feeds.length }}</span>
            </button>
            
            <!-- Folder Feeds List -->
            <div v-if="!collapsedFolders[folder.name]" class="pl-3 space-y-0.5">
              <button
                v-for="feed in folder.feeds"
                :key="feed.id"
                @click="selectFeed(feed.id)"
                class="group relative flex h-8 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-xs transition-all overflow-hidden"
                :class="selectedFeedId === feed.id ? 'bg-primary/5 text-primary font-semibold' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
              >
                <SiteIcon :icon-url="feed.icon_url || null" size="xs" rounded="sm" class="shrink-0" />
                <span class="flex-1 truncate">{{ feed.title }}</span>
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
              <h2 class="truncate text-base font-bold tracking-tight text-foreground/90">
                {{ selectedFeedTitle || selectedAccount?.name || 'RSS 阅读器' }}
              </h2>
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
          <div class="flex items-center gap-2 mt-3 w-full">
            <!-- Entry Search -->
            <div class="relative flex-1 group">
              <AppIcon name="search" class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary" />
              <input
                v-model="entrySearch"
                placeholder="搜索文章..."
                class="h-8 w-full rounded-lg border border-border/50 bg-accent/20 hover:bg-accent/40 pl-8 pr-3 text-xs outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/30 focus:bg-background"
              />
            </div>

          </div>
        </header>

        <!-- Main Body Scroll Container -->
        <div ref="entriesContainer" class="flex-1 overflow-y-auto custom-scrollbar bg-background">
          <div class="w-full p-4 space-y-4">

            <!-- Empty view -->
            <div 
              v-if="filteredEntries.length === 0" 
              class="flex min-h-[20rem] flex-col items-center justify-center text-center py-10"
            >
              <div class="h-16 w-16 rounded-full bg-accent/30 flex items-center justify-center mb-4 ring-4 ring-background shadow-inner">
                <AppIcon name="inbox" class="h-6 w-6 text-muted-foreground/45" />
              </div>
              <h3 class="text-sm font-bold tracking-tight text-foreground/80">暂无相关文章</h3>
              <p class="mt-1 text-[11px] text-muted-foreground max-w-[200px] leading-relaxed">
                {{ selectedAccount ? '当前无对应文章，可点击同步获取最新内容。' : '请先添加并选择您的 RSS 账号。' }}
              </p>
            </div>

            <!-- Articles List -->
            <div v-else class="flex flex-col divide-y divide-border/10 border-t border-b border-border/10">
              <div 
                v-for="entry in filteredEntries" 
                :key="entry.id"
                @click="openReader(entry)"
                class="group relative flex flex-col justify-between py-4 px-3.5 transition-all duration-200 ease-out cursor-pointer animate-fade-in"
                :class="readingEntry && String(readingEntry.id) === String(entry.id) ? 'bg-primary/5' : 'bg-transparent hover:bg-accent/5'"
              >
                <!-- Card Top: Category & Time -->
                <div class="flex items-center justify-between text-xs text-muted-foreground/85 mb-2">
                  <span class="inline-flex items-center text-primary text-[10px] font-bold tracking-wider uppercase">
                    {{ getFeedCategory(entry.feed_id) }}
                  </span>
                  <span class="tabular-nums text-[10px] text-muted-foreground/60">{{ formatDate(entry.published_at) }}</span>
                </div>
                
                <!-- Title & Summary -->
                <div class="flex-1 space-y-1 mb-3">
                  <h4 class="text-xs font-bold leading-snug transition-colors duration-200 ease-out line-clamp-2" :class="readingEntry && String(readingEntry.id) === String(entry.id) ? 'text-primary' : 'text-foreground/90 group-hover:text-primary'">
                    {{ entry.title }}
                  </h4>
                  <p v-if="entry.summary" class="text-[11px] leading-relaxed text-muted-foreground/70 line-clamp-2" v-html="stripHtmlTags(entry.summary)" />
                </div>
                
                <!-- Card Bottom: Source & Media indicator -->
                <div class="flex items-center justify-between pt-1">
                  <div class="flex items-center gap-2 min-w-0">
                    <SiteIcon :icon-url="getFeedIconUrl(entry.feed_id)" size="xs" rounded="sm" class="shrink-0" />
                    <span class="text-[11px] font-semibold text-muted-foreground/90 truncate">
                      {{ getFeedTitle(entry.feed_id) }}
                    </span>
                  </div>
                  
                  <AppIcon name="externalLink" class="h-3 w-3 text-muted-foreground/40 group-hover:text-foreground/80 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-200 ease-out" />
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
        <div v-if="readingEntry" class="flex flex-col h-full overflow-hidden animate-fade-in bg-background">
          <!-- Reader Header -->
          <header class="shrink-0 border-b border-border/10 p-6 flex flex-col gap-3.5 bg-background">
            <!-- Feed Source details & Date -->
            <div class="flex items-center justify-between text-xs text-muted-foreground/85">
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-bold uppercase tracking-wider text-[9px]">
                  {{ getFeedCategory(readingEntry.feed_id) }}
                </span>
                <span>•</span>
                <span class="font-bold text-foreground/80">{{ getFeedTitle(readingEntry.feed_id) }}</span>
              </div>
              
              <span class="tabular-nums text-muted-foreground/60 text-[11px]">{{ formatDate(readingEntry.published_at) }}</span>
            </div>
            
            <!-- Title -->
            <h3 class="text-xl md:text-2xl font-bold tracking-tight text-foreground leading-snug">
              {{ readingEntry.title }}
            </h3>
            
            <!-- Actions Row -->
            <div class="flex items-center justify-between mt-1 pt-3.5 border-t border-border/5">
              <div class="flex items-center gap-2">
                <a 
                  :href="readingEntry.canonical_url" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border/50 bg-accent/20 px-3 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
                >
                  <AppIcon name="externalLink" class="h-3.5 w-3.5" />
                  <span>访问原始网页</span>
                </a>
              </div>
              
              <!-- Close/Deselect button -->
              <button 
                @click="closeReader"
                class="h-8 px-3 rounded-lg border border-border/50 bg-accent/10 hover:bg-accent/25 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors text-xs font-semibold gap-1"
                title="关闭阅读器"
              >
                <AppIcon name="close" class="h-3.5 w-3.5" />
                <span>关闭</span>
              </button>
            </div>
          </header>
          
          <!-- Reader Body Scroll Container -->
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-10 bg-background space-y-6">
            <!-- Description / HTML content -->
            <div 
              class="reader-content prose prose-neutral dark:prose-invert max-w-3xl mx-auto text-foreground/90 leading-relaxed font-normal py-2 space-y-4"
              v-html="readingEntry.summary || '<p class=text-muted-foreground>该文章暂无正文内容。</p>'"
            />
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
      <DialogContent class="max-w-md overflow-hidden rounded-2xl p-0 border border-border/50 bg-background/95 backdrop-blur-xl">
        <DialogHeader class="border-b border-border/10 p-5 text-left">
          <DialogTitle class="text-base font-semibold text-foreground">
            {{ accountForm.id ? '编辑 RSS 账号' : '添加 RSS 账号' }}
          </DialogTitle>
          <DialogDescription class="text-xs text-muted-foreground mt-1 leading-normal">
            连接第三方 RSS 服务账号，支持 Google Reader API, Miniflux, Fever 等规范。
          </DialogDescription>
        </DialogHeader>
        
        <div class="p-5 space-y-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
          <!-- Provider Select -->
          <div class="space-y-1.5">
            <label class="text-xs font-bold text-muted-foreground">服务提供商</label>
            <select 
              v-model="accountForm.provider" 
              class="h-10 w-full rounded-xl border border-border/50 bg-accent/20 px-3 text-sm focus:border-primary focus:bg-background outline-none transition-all"
            >
              <option value="greader">Google Reader API</option>
              <option value="miniflux">Miniflux</option>
              <option value="fever">Fever</option>
            </select>
          </div>
          
          <!-- Account Name -->
          <div class="space-y-1.5">
            <label class="text-xs font-bold text-muted-foreground">账号名称</label>
            <Input 
              v-model="accountForm.name" 
              class="h-10 rounded-xl border-border/50 bg-accent/20 focus:bg-background text-sm shadow-none" 
              placeholder="例如: 我的 Miniflux" 
            />
          </div>
          
          <!-- Base URL -->
          <div class="space-y-1.5">
            <label class="text-xs font-bold text-muted-foreground">服务接口地址 (URL)</label>
            <Input 
              v-model="accountForm.base_url" 
              class="h-10 rounded-xl border-border/50 bg-accent/20 focus:bg-background text-sm shadow-none" 
              :placeholder="baseUrlPlaceholder" 
            />
          </div>
          
          <!-- Username -->
          <div class="space-y-1.5">
            <label class="text-xs font-bold text-muted-foreground">用户名</label>
            <Input 
              v-model="accountForm.username" 
              class="h-10 rounded-xl border-border/50 bg-accent/20 focus:bg-background text-sm shadow-none" 
              placeholder="用户名 (Google Reader 与 Fever 需要)" 
            />
          </div>
          
          <!-- Credential -->
          <div class="space-y-1.5">
            <label class="text-xs font-bold text-muted-foreground">{{ credentialPlaceholder }}</label>
            <Input 
              v-model="accountForm.credential" 
              type="password"
              class="h-10 rounded-xl border-border/50 bg-accent/20 focus:bg-background text-sm shadow-none" 
              :placeholder="accountForm.id ? '留空表示不修改密码或 Token' : '密码或 API Token'" 
            />
          </div>
          
          <!-- Enabled Switch -->
          <label class="flex items-center gap-2.5 py-1 text-sm text-muted-foreground cursor-pointer select-none">
            <input 
              v-model="accountForm.enabled" 
              type="checkbox" 
              class="h-4.5 w-4.5 rounded-lg border-border bg-accent/20 text-primary focus:ring-primary/20 accent-primary" 
            />
            <span class="font-semibold text-foreground/80">启用此账号同步</span>
          </label>
          
          <!-- Error / Success Message -->
          <div 
            v-if="formMessage" 
            class="p-3 rounded-xl border text-xs leading-relaxed"
            :class="formError ? 'border-destructive/20 bg-destructive/5 text-destructive' : 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500'"
          >
            {{ formMessage }}
          </div>
        </div>
        
        <DialogFooter class="gap-2 bg-muted/30 p-4 border-t border-border/10">
          <Button 
            type="button" 
            variant="outline" 
            class="h-10 rounded-xl text-xs font-semibold px-4 flex-1 sm:flex-none" 
            :disabled="testing || !canTestForm" 
            @click="testForm"
          >
            <AppIcon v-if="testing" name="refresh" class="h-3.5 w-3.5 mr-1.5 animate-spin" />
            测试连接
          </Button>
          <div class="flex gap-2 flex-1 sm:flex-none justify-end">
            <Button 
              type="button" 
              variant="outline" 
              class="h-10 rounded-xl text-xs font-semibold px-4" 
              @click="showAddEditModal = false"
            >
              取消
            </Button>
            <Button 
              type="button"
              class="h-10 rounded-xl text-xs font-semibold px-5" 
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

    <!-- 5. Premium Slide-over Reader View Drawer (Mobile Fallback) -->
    <Sheet :open="isMobile && !!readingEntry" @update:open="closeReader">
      <SheetContent class="w-full sm:max-w-[640px] md:max-w-[768px] lg:max-w-[900px] border-l border-border/20 bg-background/95 backdrop-blur-xl p-0 flex flex-col h-full shadow-2xl">
        <div v-if="readingEntry" class="flex flex-col h-full overflow-hidden">
          <!-- Reader Header -->
          <header class="shrink-0 border-b border-border/10 p-6 bg-background/50 backdrop-blur-sm pr-16 flex flex-col gap-2">
            <!-- Feed Source details & Date -->
            <div class="flex items-center gap-2.5 text-xs text-muted-foreground">
              <span class="px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-bold uppercase tracking-wider text-[9px]">
                {{ getFeedCategory(readingEntry.feed_id) }}
              </span>
              <span>•</span>
              <span class="font-bold text-foreground/80">{{ getFeedTitle(readingEntry.feed_id) }}</span>
              <span>•</span>
              <span>发布于 {{ formatDate(readingEntry.published_at) }}</span>
            </div>
            
            <!-- Title -->
            <h3 class="text-base md:text-lg font-bold tracking-tight text-foreground leading-snug">
              {{ readingEntry.title }}
            </h3>
            
            <!-- Actions -->
            <div class="flex items-center gap-3 mt-1.5">
              <a 
                :href="readingEntry.canonical_url" 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border/50 bg-accent/20 px-3 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
              >
                <AppIcon name="externalLink" class="h-3.5 w-3.5" />
                <span>访问原始网页</span>
              </a>
            </div>
          </header>
          
          <!-- Reader Body Scroll Container -->
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
            <!-- Description / HTML content -->
            <div 
              class="reader-content prose prose-sm dark:prose-invert max-w-none text-foreground/90 leading-relaxed font-normal py-2 space-y-4"
              v-html="readingEntry.summary || '<p class=text-muted-foreground>该文章暂无正文内容。</p>'"
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { onClickOutside } from '@vueuse/core'
import {
  createRssAccount,
  deleteRssAccount,
  getRssAccounts,
  getRssEntries,
  getRssFeeds,
  getRssSyncStatus,
  syncRssAccount,
  testRssAccountConfig,
  updateRssAccount,
} from '@/api'
import AppIcon from '@/components/common/AppIcon.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { formatDate } from '../utils/dateFormat'

type ApiResult<T = any> = { data: T | null; error: any | null }
type RssAccount = {
  id: number
  provider: string
  name: string
  base_url: string
  username?: string | null
  enabled: boolean
  last_sync_at?: string | null
  last_error?: string | null
  created_at?: string | null
  updated_at?: string | null
}
type RssFeed = {
  id: number
  account_id: number
  title: string
  feed_url?: string | null
  site_url?: string | null
  icon_url?: string | null
  category?: string | null
}
type RssEntry = {
  id: number
  account_id: number
  feed_id: number
  external_entry_id: string
  canonical_url: string
  title: string
  summary?: string | null
  thumbnail?: string | null
  author?: string | null
  published_at?: string | null
  is_read: boolean
  is_starred: boolean
}

// Reactive Data State
const accounts = ref<RssAccount[]>([])
const feeds = ref<RssFeed[]>([])
const entries = ref<RssEntry[]>([])
const selectedAccountId = ref<number | null>(null)
const selectedFeedId = ref<number | null>(null)

// UI Loading/Transition states
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const syncing = ref(false)
const statusMessage = ref('')
const statusError = ref(false)

// Modals, Dropdowns & Sidebar Search
const showAddEditModal = ref(false)
const showDeleteConfirmModal = ref(false)
const accountToDelete = ref<RssAccount | null>(null)
const showAccountDropdown = ref(false)
const accountDropdownRef = ref<HTMLElement | null>(null)
const showSyncMenu = ref(false)
const syncDropdownRef = ref<HTMLElement | null>(null)
const feedSearch = ref('')
const collapsedFolders = ref<Record<string, boolean>>({})

// Articles grid Filtering, Searching & Pagination
const entrySearch = ref('')
const page = ref(1)
const pageSize = ref(30)
const totalEntries = ref(0)
const loadingMoreEntries = ref(false)
const readingEntry = ref<RssEntry | null>(null)
const isMobile = ref(false)

// Scroll containers and Infinite scroll observer refs
const entriesContainer = ref<HTMLElement | null>(null)
const loadMoreTrigger = ref<HTMLElement | null>(null)
let entriesObserver: IntersectionObserver | null = null

// Account Form state
const accountForm = ref({
  id: null as number | null,
  provider: 'greader',
  name: '',
  base_url: '',
  username: '',
  credential: '',
  enabled: true,
})
const formMessage = ref('')
const formError = ref(false)

// Click outside account dropdown logic
onClickOutside(accountDropdownRef, () => {
  showAccountDropdown.value = false
})
onClickOutside(syncDropdownRef, () => {
  showSyncMenu.value = false
})

// Computeds
const selectedAccount = computed(() => accounts.value.find((account) => account.id === selectedAccountId.value) || null)

const defaultAccountName = computed(() => {
  const baseUrl = accountForm.value.base_url.trim()
  if (baseUrl) {
    try {
      return new URL(baseUrl).host
    } catch {
      return baseUrl
    }
  }
  return accountForm.value.provider
})

const baseUrlPlaceholder = computed(() => {
  if (accountForm.value.provider === 'greader') return 'https://reader.example.com/api/greader.php'
  return 'https://reader.example.com'
})

const credentialPlaceholder = computed(() => {
  if (accountForm.value.provider === 'miniflux') return 'API Token'
  return 'API 密码或 Token'
})

const filteredFeeds = computed(() => {
  if (!selectedAccountId.value) return feeds.value
  return feeds.value.filter((feed) => feed.account_id === selectedAccountId.value)
})

const canSaveForm = computed(() => {
  return !!accountForm.value.base_url.trim() && (!!accountForm.value.id || !!accountForm.value.credential.trim())
})

const canTestForm = computed(() => {
  return !!accountForm.value.base_url.trim() && !!accountForm.value.credential.trim()
})

const hasMoreEntries = computed(() => entries.value.length < totalEntries.value)

// Categories / Folders collapsible tree grouping
const feedFolders = computed(() => {
  const groups: Record<string, RssFeed[]> = {}
  const query = feedSearch.value.trim().toLowerCase()
  const feedsToGroup = filteredFeeds.value.filter(feed => {
    if (!query) return true
    return feed.title.toLowerCase().includes(query) || 
           (feed.feed_url && feed.feed_url.toLowerCase().includes(query)) ||
           (feed.category && feed.category.toLowerCase().includes(query))
  })
  
  feedsToGroup.forEach(feed => {
    const cat = feed.category || '未分类'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(feed)
  })
  
  return Object.entries(groups).map(([name, feeds]) => ({ name, feeds }))
})

// Article grid titles & totals
const selectedFeedTitle = computed(() => {
  if (selectedFeedId.value) {
    return feeds.value.find(f => f.id === selectedFeedId.value)?.title || '订阅源'
  }
  return null
})

const selectedFeedSubtitle = computed(() => {
  if (selectedFeedId.value) {
    const feed = feeds.value.find(f => f.id === selectedFeedId.value)
    return `${feed?.category || '未分类'} · ${totalEntries.value} 篇文章`
  }
  if (selectedAccount.value) {
    return `共 ${totalEntries.value} 篇文章`
  }
  return '浏览您的 RSS 服务内容源'
})

// Client side filtering for article cards
const filteredEntries = computed(() => {
  let list = entries.value
  const query = entrySearch.value.trim().toLowerCase()
  
  if (query) {
    list = list.filter(entry => {
      const matchTitle = entry.title.toLowerCase().includes(query)
      const matchSummary = entry.summary ? entry.summary.toLowerCase().includes(query) : false
      return matchTitle || matchSummary
    })
  }
  
  return list
})

// Helper methods for resolving article grid metadata
const getFeedTitle = (feedId: number) => {
  const feed = feeds.value.find(f => f.id === feedId)
  return feed ? feed.title : '未知源'
}

const getFeedCategory = (feedId: number) => {
  const feed = feeds.value.find(f => f.id === feedId)
  return feed ? feed.category || '未分类' : '未分类'
}

const getFeedIconUrl = (feedId: number) => {
  const feed = feeds.value.find(f => f.id === feedId)
  return feed?.icon_url || null
}

const getFeedInitials = (feedId: number) => {
  const title = getFeedTitle(feedId)
  return title.trim().charAt(0) || 'R'
}

// Clean summary HTML tags for compact card summary rendering
const stripHtmlTags = (html: string) => {
  if (!html) return ''
  let text = html.replace(/<(script|style)\b[^>]*>([\s\S]*?)<\/\1>/gi, '')
  text = text.replace(/<[^>]+>/g, ' ')
  text = text
    .replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
  return text.replace(/\s+/g, ' ').trim()
}

let statusTimeout: ReturnType<typeof setTimeout> | null = null
const setStatus = (message: string, isError = false) => {
  statusMessage.value = message
  statusError.value = isError
  
  if (statusTimeout) clearTimeout(statusTimeout)
  if (message && !message.startsWith('同步中')) {
    statusTimeout = setTimeout(() => {
      statusMessage.value = ''
      statusError.value = false
    }, 6000)
  }
}

const resetScroll = () => {
  if (entriesContainer.value) {
    entriesContainer.value.scrollTop = 0
  }
}

const resetForm = () => {
  accountForm.value = {
    id: null,
    provider: 'greader',
    name: '',
    base_url: '',
    username: '',
    credential: '',
    enabled: true,
  }
  formMessage.value = ''
  formError.value = false
}

const openAddAccount = () => {
  resetForm()
  showAddEditModal.value = true
}

const openEditAccount = (account: RssAccount) => {
  accountForm.value = {
    id: account.id,
    provider: account.provider,
    name: account.name,
    base_url: account.base_url,
    username: account.username || '',
    credential: '',
    enabled: account.enabled,
  }
  formMessage.value = ''
  formError.value = false
  showAddEditModal.value = true
}

const confirmDeleteAccount = (account: RssAccount) => {
  accountToDelete.value = account
  showDeleteConfirmModal.value = true
}

const handleDeleteAccount = async () => {
  if (!accountToDelete.value) return
  loading.value = true
  const result = await deleteRssAccount(accountToDelete.value.id)
  loading.value = false
  if (result.error) {
    setStatus(result.error.message || '删除账号失败', true)
    showDeleteConfirmModal.value = false
    return
  }
  
  setStatus(`已成功删除账号「${accountToDelete.value.name}」`)
  showDeleteConfirmModal.value = false
  if (selectedAccountId.value === accountToDelete.value.id) {
    selectedAccountId.value = null
    selectedFeedId.value = null
  }
  accountToDelete.value = null
  await loadAll()
}

const toggleFolder = (name: string) => {
  collapsedFolders.value[name] = !collapsedFolders.value[name]
}

const loadAccounts = async () => {
  const result = await getRssAccounts() as ApiResult<{ data: RssAccount[] }>
  if (result.error) {
    setStatus(result.error.message || '加载 RSS 账号失败', true)
    return
  }
  accounts.value = result.data?.data || []
  if (!selectedAccountId.value && accounts.value.length) {
    selectedAccountId.value = accounts.value[0].id
  }
}

const loadFeeds = async () => {
  const result = await getRssFeeds(selectedAccountId.value ? { accountId: selectedAccountId.value } : {}) as ApiResult<{ data: RssFeed[] }>
  if (result.error) {
    setStatus(result.error.message || '加载 Feed 失败', true)
    return
  }
  feeds.value = result.data?.data || []
}

const loadEntries = async (isReset = false) => {
  if (isReset) {
    page.value = 1
    entries.value = []
    resetScroll()
  }
  const params: Record<string, unknown> = { page: page.value, pageSize: pageSize.value }
  if (selectedAccountId.value) params.accountId = selectedAccountId.value
  if (selectedFeedId.value) params.feedId = selectedFeedId.value
  
  if (isReset) loading.value = true
  else loadingMoreEntries.value = true
  
  const result = await getRssEntries(params) as ApiResult<{ data: RssEntry[], total: number }>
  
  if (isReset) loading.value = false
  else loadingMoreEntries.value = false
  
  if (result.error) {
    setStatus(result.error.message || '加载条目失败', true)
    return
  }
  
  const fetched = result.data?.data || []
  totalEntries.value = (result.data as any)?.total || 0
  
  if (isReset) {
    entries.value = fetched
  } else {
    entries.value.push(...fetched)
  }
}

const loadMore = async () => {
  if (loadingMoreEntries.value || !hasMoreEntries.value) return
  page.value += 1
  await loadEntries(false)
}

const loadAll = async () => {
  loading.value = true
  await loadAccounts()
  await loadFeeds()
  await loadEntries(true)
  loading.value = false
}

const selectAccount = async (accountId: number) => {
  selectedAccountId.value = accountId
  selectedFeedId.value = null
  await loadFeeds()
  await loadEntries(true)
}

const selectFeed = async (feedId: number) => {
  selectedFeedId.value = selectedFeedId.value === feedId ? null : feedId
  await loadEntries(true)
}

const saveAccount = async () => {
  saving.value = true
  formMessage.value = ''
  const payload: Record<string, unknown> = {
    provider: accountForm.value.provider,
    name: accountForm.value.name.trim() || defaultAccountName.value,
    base_url: accountForm.value.base_url,
    username: accountForm.value.username,
    enabled: accountForm.value.enabled,
  }
  if (accountForm.value.credential.trim()) {
    payload.credential = accountForm.value.credential
  }
  const result = accountForm.value.id
    ? await updateRssAccount(accountForm.value.id, payload)
    : await createRssAccount(payload as any)
  saving.value = false
  if (result.error) {
    formError.value = true
    formMessage.value = result.error.message || '保存失败'
    return
  }
  formError.value = false
  formMessage.value = '已保存'
  showAddEditModal.value = false
  resetForm()
  await loadAll()
}

const testForm = async () => {
  testing.value = true
  formMessage.value = ''
  const result = await testRssAccountConfig({
    provider: accountForm.value.provider,
    name: accountForm.value.name || accountForm.value.provider,
    base_url: accountForm.value.base_url,
    username: accountForm.value.username,
    credential: accountForm.value.credential,
  })
  testing.value = false
  formError.value = !!result.error
  formMessage.value = result.error ? result.error.message || '连接失败' : `连接成功，发现 ${(result.data as any)?.feed_count ?? 0} 个 Feed`
}

let syncPollTimer: ReturnType<typeof setInterval> | null = null

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
    if (data.running) {
      const phaseLabel: Record<string, string> = {
        starting: '启动中',
        feeds_fetching: '获取 Feed 列表',
        feeds_saving: '保存 Feed',
        entries_fetching: '获取文章',
        entries_saving: '保存文章',
      }
      const label = phaseLabel[data.phase] || data.phase
      let progress = ''
      if (data.phase === 'entries_fetching') {
        progress = data.entries_fetched != null ? `已拉取 ${data.entries_fetched} 条` : '等待服务器响应...'
      } else if (data.phase === 'entries_saving') {
        progress = `已保存 ${data.entries_synced || 0} 条`
      } else if (data.feeds_synced != null) {
        progress = `${data.feeds_synced} 个`
      }
      setStatus(`同步中 [${label}] ${progress}`, false)
    } else {
      clearInterval(syncPollTimer!)
      syncPollTimer = null
      syncing.value = false
      if (data.phase === 'completed') {
        setStatus(`同步完成：${data.feeds_synced || 0} 个 Feed，${data.entries_synced || 0} 个文章`)
      } else {
        setStatus(data.message || data.error || '同步失败', true)
      }
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

const openReader = (entry: RssEntry) => {
  readingEntry.value = entry
}

const closeReader = () => {
  readingEntry.value = null
}

// Infinite Scroll Automatic Observer Setup
const initObserver = () => {
  entriesObserver?.disconnect()
  entriesObserver = new IntersectionObserver((entriesList) => {
    if (entriesList[0].isIntersecting && !loading.value && !loadingMoreEntries.value && hasMoreEntries.value) {
      loadMore()
    }
  }, {
    root: entriesContainer.value,
    rootMargin: '400px'
  })
  if (loadMoreTrigger.value) {
    entriesObserver.observe(loadMoreTrigger.value)
  }
}

// Watchers
watch(selectedAccountId, () => {
  collapsedFolders.value = {}
})

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

const checkIfMobile = () => {
  isMobile.value = window.innerWidth < 1024
}

onMounted(async () => {
  checkIfMobile()
  window.addEventListener('resize', checkIfMobile)
  await loadAll()
  nextTick(() => {
    initObserver()
  })
  await resumeSyncPollingIfRunning()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkIfMobile)
  entriesObserver?.disconnect()
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

/* Scoped stylesheet for beautiful markdown / HTML summary rendering in reader */
.reader-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.75rem;
  margin: 1.5rem auto;
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.reader-content :deep(a) {
  color: hsl(var(--primary));
  text-decoration: underline;
  font-weight: 500;
  transition: opacity 0.15s;
}

.reader-content :deep(a:hover) {
  opacity: 0.8;
}

.reader-content :deep(p) {
  margin-bottom: 1.25rem;
  line-height: 1.7;
}

.reader-content :deep(h1),
.reader-content :deep(h2),
.reader-content :deep(h3),
.reader-content :deep(h4) {
  font-weight: 700;
  color: var(--foreground);
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
}

.reader-content :deep(blockquote) {
  border-left: 4px solid hsl(var(--primary));
  padding-left: 1.25rem;
  color: var(--muted-foreground);
  font-style: italic;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 0.375rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
  margin: 1.5rem 0;
}

.reader-content :deep(ul),
.reader-content :deep(ol) {
  padding-left: 1.25rem;
  margin-bottom: 1.25rem;
}

.reader-content :deep(li) {
  margin-bottom: 0.5rem;
  list-style-type: disc;
}

.reader-content :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 0.75rem;
  padding: 1rem;
  overflow-x: auto;
  font-family: monospace;
  font-size: 0.85rem;
  margin: 1.5rem 0;
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
