import { computed, reactive, toRefs } from 'vue'

export type SyncTimeLens = 'now' | '24h' | '7d'
export type SyncFocusKind = 'overview' | 'site' | 'failed-runs' | 'slow-runs' | 'recovery'

export interface SyncWorkbenchState {
  lens: SyncTimeLens
  focus: SyncFocusKind
  site: string
  selectedRunId: string
  selectedSubscriptionId: number | null
}

export function useSyncCenterWorkbench(initialState: Partial<SyncWorkbenchState> = {}) {
  const state = reactive<SyncWorkbenchState>({
    lens: initialState.lens || 'now',
    focus: initialState.focus || 'overview',
    site: initialState.site || '',
    selectedRunId: initialState.selectedRunId || '',
    selectedSubscriptionId: initialState.selectedSubscriptionId ?? null,
  })

  const analysisVisible = computed(() => {
    return state.focus !== 'overview' || !!state.site || !!state.selectedRunId || state.selectedSubscriptionId !== null
  })

  const setLens = (lens: SyncTimeLens) => {
    state.lens = lens
  }

  const setFocus = (focus: SyncFocusKind) => {
    state.focus = focus
  }

  const setSite = (site: string) => {
    state.site = site
  }

  const selectRun = (runId: string) => {
    state.selectedRunId = runId
  }

  const selectSubscription = (subscriptionId: number | null) => {
    state.selectedSubscriptionId = subscriptionId
  }

  const resetAnalysis = () => {
    state.focus = 'overview'
    state.site = ''
    state.selectedRunId = ''
    state.selectedSubscriptionId = null
  }

  return {
    ...toRefs(state),
    analysisVisible,
    resetAnalysis,
    selectRun,
    selectSubscription,
    setFocus,
    setLens,
    setSite,
    state,
  }
}
