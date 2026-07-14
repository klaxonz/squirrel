/**
 * Resolve a caught value into a user-facing error message.
 *
 * The `err instanceof Error ? err.message : <fallback>` idiom was copy-pasted
 * across ~40 call sites (music / playback / rss / video / settings). This helper
 * is the single source of truth for that mapping. Callers pass the fallback they
 * want, so the per-feature wording stays local.
 *
 * @param err    the caught value (unknown)
 * @param fallback  returned when err isn't an Error with a usable message
 */
export const errorMessage = (err: unknown, fallback: string): string => {
  if (err instanceof Error && err.message) return err.message
  return fallback
}
