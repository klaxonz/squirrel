import { computed, type ComputedRef } from 'vue'
import type { PlayerRuntimeStore } from '../runtime/PlayerStore'
import type { IconName } from '../core/useIcons'

export interface UseSleepTimerOptions {
  store: PlayerRuntimeStore
  pause: () => void
  showCentralHud: (type: string, value: string, icon: IconName) => void
  t?: (key: string, params?: Record<string, string | number>) => string
}

export interface UseSleepTimerReturn {
  sleepTimerOptions: number[]
  sleepTimerLabel: ComputedRef<string>
  formatSleepRemaining: () => string
  handleSleepTimerSelect: (mins: number | null) => void
  stopSleepTimer: () => void
  startSleepTimer: () => void
}

export function useSleepTimer(options: UseSleepTimerOptions): UseSleepTimerReturn {
  const { store, pause, showCentralHud, t } = options

  const sleepTimerOptions = [15, 30, 45, 60, 90, 120]

  let sleepTimerInterval: ReturnType<typeof setInterval> | null = null

  const sleepTimerLabel = computed(() => {
    if (t) {
      if (store.sleepTimerMinutes === null) return t('sleepTimerOff')
      return t('sleepTimerMinutes', { minutes: store.sleepTimerMinutes })
    }
    if (store.sleepTimerMinutes === null) return 'Sleep Timer: Off'
    return `Sleep Timer: ${store.sleepTimerMinutes} min`
  })

  const formatSleepRemaining = (): string => {
    const total = store.sleepTimerRemaining
    const mins = Math.floor(total / 60)
    const secs = Math.floor(total % 60)
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  const startSleepTimer = () => {
    stopSleepTimer()
    sleepTimerInterval = setInterval(() => {
      if (store.sleepTimerRemaining > 0) {
        store.setSleepTimerRemaining(store.sleepTimerRemaining - 1)
      } else {
        pause()
        store.setSleepTimerMinutes(null)
        store.setSleepTimerRemaining(0)
        stopSleepTimer()
        showCentralHud('sleep', t ? t('sleepTimer') : 'Sleep Timer', 'pause')
      }
    }, 1000)
  }

  const stopSleepTimer = () => {
    if (sleepTimerInterval) {
      clearInterval(sleepTimerInterval)
      sleepTimerInterval = null
    }
  }

  const handleSleepTimerSelect = (mins: number | null) => {
    store.setSleepTimerMinutes(mins)
    if (mins !== null) {
      store.setSleepTimerRemaining(mins * 60)
      startSleepTimer()
    } else {
      stopSleepTimer()
    }
  }

  return {
    sleepTimerOptions,
    sleepTimerLabel,
    formatSleepRemaining,
    handleSleepTimerSelect,
    stopSleepTimer,
    startSleepTimer,
  }
}
