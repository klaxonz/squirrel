import { QueryClient, MutationCache, type QueryClientConfig } from '@tanstack/vue-query'
import { useToast } from '@/shared/components/toast/useToast'
import { ApiError } from '@/shared/lib/apiError'

/**
 * Central vue-query configuration. The single source of truth for default
 * caching, retry, and — most importantly — the global error-feedback policy.
 *
 * ## Error model
 * `get/post/...` in `request.ts` THROW `ApiError` on failure (they no longer
 * return `{ data, error }`). vue-query is therefore the one channel through
 * which every API error flows. This file decides what happens to those errors:
 *
 * - **Mutations** → auto-`toast.error(message)` via `MutationCache.onError`,
 *   UNLESS the mutation opted out with `meta: { silent: true }` (inline-error
 *   forms, optimistic updates that roll back silently, status-callback flows).
 *   This replaces the ~14 hand-rolled `if (result.error) toast.error(...)` sites.
 * - **Queries** → silent by default (loaders failing is routine; each view
 *   renders its own error UI via `AppEmptyState variant="error"` from PR2).
 *
 * ## Defaults rationale
 * - `staleTime: 30s` — desktop app; avoid hammering the backend on every mount.
 * - `refetchOnWindowFocus: false` — Electron window focus isn't a meaningful
 *   "user returned to the app" signal here, and unexpected refetches disrupt.
 * - `retry: 1` — one retry covers transient network blips without masking real
 *   failures behind long retry chains.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  } satisfies QueryClientConfig['defaultOptions'],
  // ponytail: global mutation error feedback. Replaces the per-call
  // `if (result.error) toast.error(...)` boilerplate that was duplicated across
  // ~14 sites. Mutations that need inline error display or silent optimistic
  // rollback pass `meta: { silent: true }` to opt out.
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (mutation.options.meta?.silent) return
      const message = error instanceof ApiError ? error.message : '操作失败，请稍后重试'
      useToast().error(message)
    },
  }),
})

/**
 * Query-key factory. Centralising keys prevents typo-driven cache misses and
 * makes `invalidateQueries` calls readable. Add namespaces as features migrate.
 *
 * Convention: `[domain, ...scopes]` tuples — vue-query serialises arrays stably.
 */
export const queryKeys = {
  tasks: {
    all: ['tasks'] as const,
    list: (params: Record<string, unknown>) => ['tasks', 'list', params] as const,
    statistics: ['tasks', 'statistics'] as const,
    classes: ['tasks', 'classes'] as const,
  },
  user: {
    me: ['user', 'me'] as const,
  },
} as const
