/**
 * Pure converters for the site-config editor form.
 *
 * These bridge the form's text-friendly representations and the backend's
 * structured payloads: header maps <-> `Key: value` text, list text <-> arrays,
 * and string inputs <-> `number | undefined`. Extracted from
 * SiteConfigEditorDialog.vue as pure, reusable utilities so the form composable
 * can stay focused on state + validation + serialization.
 */

/**
 * Serialise a header map into newline-joined `Key: value` text.
 */
export const headersToText = (headers: Record<string, string> = {}): string =>
  Object.entries(headers || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n')

/**
 * Parse newline/comma-separated text into a de-duplicated, trimmed string list.
 */
export const parseListInput = (text = ''): string[] =>
  text
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)

/**
 * Parse `Key: value` (newline-separated) text back into a header map. Values
 * may themselves contain colons — only the first splits the key off.
 */
export const parseHeadersText = (text = ''): Record<string, string> => {
  const result: Record<string, string> = {}
  text.split('\n').forEach((line) => {
    const trimmed = line.trim()
    if (!trimmed) return
    const [key, ...rest] = trimmed.split(':')
    if (!key) return
    result[key.trim()] = rest.join(':').trim()
  })
  return result
}

/**
 * Coerce a form string into a number, or `undefined` when empty/invalid. Used
 * for the optional numeric proxy/rate-limit/login fields — `undefined` means
 * "don't send this key" in the payload.
 */
export const toNumberOrUndefined = (value: unknown): number | undefined => {
  if (value === '' || value === null || value === undefined) return undefined
  const num = Number(value)
  return Number.isNaN(num) ? undefined : num
}
