import type { ClassValue } from 'clsx'
import type { Ref } from 'vue'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// A minimal "updater" type used by some UI patterns.
// Avoids pulling in TanStack Table types since we don't depend on it.
export type Updater<T> = T | ((old: T) => T)

export function valueUpdater<T>(updaterOrValue: Updater<T>, ref: Ref<T>) {
  ref.value = typeof updaterOrValue === 'function'
    ? (updaterOrValue as (old: T) => T)(ref.value)
    : updaterOrValue
}
