import { onScopeDispose, type Ref } from 'vue'

type PointerOutsideTarget = Ref<HTMLElement | null>

export function usePointerOutside(
  targets: PointerOutsideTarget | PointerOutsideTarget[],
  handler: (event: PointerEvent) => void,
) {
  const targetList = Array.isArray(targets) ? targets : [targets]

  const handlePointerDown = (event: PointerEvent) => {
    const target = event.target
    if (!(target instanceof Node)) return

    const isInside = targetList.some((targetRef) => targetRef.value?.contains(target))
    if (!isInside) {
      handler(event)
    }
  }

  document.addEventListener('pointerdown', handlePointerDown)
  onScopeDispose(() => document.removeEventListener('pointerdown', handlePointerDown))
}
