import { ref, watch, type Ref } from 'vue'

import type { MusicDetailIdentity, MusicDetailView } from './useMusicNavigation'

export type MusicDetailRoute = {
  view: MusicDetailView
  identity: MusicDetailIdentity | null
}

type MusicRouteRestorationOptions = {
  route: Ref<MusicDetailRoute | null>
  restore: (route: MusicDetailRoute) => Promise<boolean>
  fallback: (route: MusicDetailRoute) => void
}

function routeKey(route: MusicDetailRoute | null): string {
  if (!route) return ''
  const { identity } = route
  return [route.view, identity?.id, identity?.kind, identity?.rankCid].join(':')
}

/** Serializes detail restoration so stale route requests never become visible. */
export function useMusicRouteRestoration(options: MusicRouteRestorationOptions) {
  const restoring = ref(false)
  let activeKey = ''
  let pending: MusicDetailRoute | null = null
  let running = false

  async function drain() {
    if (running) return
    running = true

    while (pending) {
      const request = pending
      const requestKey = routeKey(request)
      pending = null

      let restored = false
      try {
        restored = await options.restore(request)
      } catch {
        restored = false
      }

      if (pending || requestKey !== activeKey) continue
      if (!restored) options.fallback(request)
      restoring.value = false
    }

    running = false
  }

  watch(
    options.route,
    (route) => {
      activeKey = routeKey(route)
      pending = route
      restoring.value = Boolean(route)
      if (route) void drain()
    },
    { immediate: true },
  )

  return { restoring }
}
