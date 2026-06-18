type MouseEventLike = {
  type: string
  clientX?: number
  clientY?: number
  currentTarget?: unknown
  target?: unknown
}

export type DebouncedFunction<TArgs extends unknown[]> = ((...args: TArgs) => void) & { cancel: () => void }

export function debounce<TArgs extends unknown[]>(fn: (...args: TArgs) => void, delay = 100): DebouncedFunction<TArgs> {
  let timer: number | null = null

  function clearTimer() {
    if (!timer) return
    clearTimeout(timer)
    timer = null
  }

  const debouncedFn = function (this: unknown, ...args: TArgs) {
    clearTimer()

    // ponytail: trim mousemove events to the fields the handlers read, to cut
    // allocation churn during high-frequency pointer scrubbing.
    const firstArg = args[0] as unknown
    if (firstArg && typeof firstArg === 'object' && (firstArg as MouseEventLike).type === 'mousemove') {
      const evt = firstArg as MouseEventLike
      args[0] = {
        clientX: evt.clientX,
        clientY: evt.clientY,
        currentTarget: evt.currentTarget,
        target: evt.target,
      } as TArgs[0]
    }

    timer = window.setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  } as DebouncedFunction<TArgs>

  debouncedFn.cancel = clearTimer

  return debouncedFn
}

export default debounce

