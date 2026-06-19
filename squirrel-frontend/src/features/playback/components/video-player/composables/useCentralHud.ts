import { ref, type Ref } from 'vue'
import type { IconName } from '../core/useIcons'

export interface CentralHudState {
  visible: boolean
  type: string
  value: string
  icon: IconName
  percent: number
}

export interface UseCentralHudReturn {
  centralHud: Ref<CentralHudState>
  showCentralHud: (type: string, value: string, icon: IconName, percent?: number) => void
  hideCentralHud: () => void
}

export function useCentralHud(): UseCentralHudReturn {
  const centralHud = ref<CentralHudState>({
    visible: false,
    type: '',
    value: '',
    icon: 'play',
    percent: 0,
  })

  let centralHudTimer: ReturnType<typeof setTimeout> | undefined

  const hideCentralHud = () => {
    centralHud.value.visible = false
  }

  const showCentralHud = (type: string, value: string, icon: IconName, percent: number = 0) => {
    clearTimeout(centralHudTimer)
    centralHud.value = { visible: true, type, value, icon, percent }
    centralHudTimer = setTimeout(hideCentralHud, 1500)
  }

  return {
    centralHud,
    showCentralHud,
    hideCentralHud,
  }
}
