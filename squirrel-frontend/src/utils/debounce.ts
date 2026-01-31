export type DebouncedFunction<TArgs extends any[]> = ((...args: TArgs) => void) & { cancel: () => void }

export function debounce<TArgs extends any[]>(fn: (...args: TArgs) => void, delay = 100): DebouncedFunction<TArgs> {
  let timer: number | null = null

  function clearTimer() {
    if (!timer) return
    clearTimeout(timer)
    timer = null
  }

  const debouncedFn = function (this: unknown, ...args: TArgs) {
    clearTimer()

    const firstArg: any = args[0]
    if (firstArg && typeof firstArg === 'object' && firstArg.type === 'mousemove') {
      args[0] = {
        clientX: firstArg.clientX,
        clientY: firstArg.clientY,
        currentTarget: firstArg.currentTarget,
        target: firstArg.target,
      }
    }

    timer = window.setTimeout(() => {
      fn.apply(this as any, args)
    }, delay)
  } as DebouncedFunction<TArgs>

  debouncedFn.cancel = clearTimer

  return debouncedFn
}

export default debounce

