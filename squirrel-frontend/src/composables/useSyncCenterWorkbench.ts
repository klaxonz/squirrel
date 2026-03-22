import { reactive, toRefs } from 'vue'

export type SyncTimeLens = 'now' | '24h' | '7d'

export interface SyncWorkbenchState {
  lens: SyncTimeLens
  selectedRunId: string
}

export function useSyncCenterWorkbench(initialState: Partial<SyncWorkbenchState> = {}) {
  const state = reactive<SyncWorkbenchState>({
    lens: initialState.lens || 'now',
    selectedRunId: initialState.selectedRunId || '',
  })

  const setLens = (lens: SyncTimeLens) => {
    state.lens = lens
  }

  const selectRun = (runId: string) => {
    state.selectedRunId = runId
  }

  const resetAnalysis = () => {
    state.selectedRunId = ''
  }

  return {
    ...toRefs(state),
    resetAnalysis,
    selectRun,
    setLens,
    state,
  }
}
