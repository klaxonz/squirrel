import type { Router } from 'vue-router'

import {
  useProfileNavigation,
} from '@/features/video/composables/useProfileNavigation'

/**
 * Card navigation facade. Prefer openProfile for avatar/name clicks;
 * openSubscription remains for known subscription ids only.
 */
export function useVideoCardNavigation(router: Router) {
  return useProfileNavigation(router)
}
